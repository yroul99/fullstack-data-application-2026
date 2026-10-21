# Review — migrations, exceptions, N+1, contrat frontend

## Étape 1 — Questions de compréhension

**Hôte dans `DATABASE_URL` : `db`.** Le backend tourne dans un conteneur : `db` est le nom du
service Compose, résolu par le DNS interne du réseau Docker. Dans le conteneur, `localhost`
désigne le conteneur backend lui-même, où il n'y a pas de PostgreSQL.

**Point de contrôle `get_db`.** Si une route lève une exception après un `db.add(...)`, le
`except` de `get_db` fait un `rollback()` : l'objet n'est **pas** en base (même si un `flush()` a
déjà envoyé l'`INSERT`, il n'a jamais été validé). Vérifié à l'étape 4.

## Étape 3bis — Le piège du renommage

Données de départ : deux items (Vélo de ville 8.50, Perceuse 5.00).

**Migration générée** après avoir renommé `tarif_jour` en `prix_jour` dans le modèle `Item` :

```python
def upgrade() -> None:
    op.add_column('items', sa.Column('prix_jour', sa.Numeric(precision=8, scale=2), nullable=False))
    op.drop_column('items', 'tarif_jour')
```

Alembic ne voit pas un renommage : il voit une colonne supprimée et une colonne ajoutée.

**Prédiction.** L'`add_column` d'une colonne `NOT NULL` sans valeur par défaut échoue sur une table
qui contient déjà des lignes. Et même si elle passait (colonne nullable, ou table vide), le
`drop_column` supprimerait `tarif_jour` : les tarifs des deux items seraient **perdus**.

**Vérification** (`alembic upgrade head` sur la migration générée) :
`psycopg.errors.NotNullViolation: column "prix_jour" of relation "items" contains null values`.
La migration est annulée en entier (DDL transactionnel) : la base reste en `c206aba807eb`, les
tarifs sont intacts.

**Correction à la main :**

```python
def upgrade() -> None:
    op.alter_column("items", "tarif_jour", new_column_name="prix_jour")


def downgrade() -> None:
    op.alter_column("items", "prix_jour", new_column_name="tarif_jour")
```

Après `upgrade head`, `SELECT id, titre, prix_jour FROM items;` renvoie toujours 8.50 et 5.00, et
la contrainte `tarif_jour_positif` porte désormais sur `prix_jour`. Puis `downgrade -1`, fichier
supprimé, modèle remis à `tarif_jour` : `alembic check` ne détecte plus aucune différence.

## Étape 4 — Traduction des exceptions métier

**Choix : un gestionnaire d'exceptions global** (`@app.exception_handler(DomainError)` dans
`main.py`, avec la table `STATUS_PAR_EXCEPTION`). La correspondance exception → code HTTP est
écrite une seule fois, donc cohérente dans toute l'API par construction, et les routes restent
réduites à « schéma en entrée, appel au service, schéma en sortie », sans `try`/`except` répété.

**Point de contrôle de l'étape 1, vérifié.** `POST /items` avec `owner_id: 999` :

- avant correction : **`500`** (`psycopg.errors.ForeignKeyViolation` sur `items_owner_id_fkey`,
  remontée telle quelle par SQLAlchemy). En base, `SELECT count(*) FROM items WHERE titre='Fantome'`
  renvoie `0` : le `rollback()` de `get_db` a bien annulé l'insertion ;
- une `500` n'est pas le bon code : c'est la base qui a détecté le problème, alors que « le
  propriétaire doit exister » est une règle métier. C'est donc au **service** de la vérifier :
  `ItemService.create` demande l'utilisateur au `UserRepository` et lève `RessourceIntrouvable`
  s'il n'existe pas ;
- après correction : **`404`** `{"detail": "Utilisateur 999 introuvable"}`.

Remarque : l'`INSERT` refusé a quand même consommé une valeur de la séquence `items_id_seq`
(les séquences ne sont pas annulées par un `rollback`), et PostgreSQL saute jusqu'à 32 valeurs
après un redémarrage. Les identifiants ne sont donc pas contigus : c'est normal.

## Étape 5 — Le N+1 sur `GET /items`

`ItemRead` contient désormais un champ `owner` (schéma `OwnerRead` : `id` et `display_name`
seulement, ni `email` ni `password_hash`). Jeu de données : 23 items répartis entre 3
propriétaires (20 insérés par `INSERT ... SELECT ... generate_series(1, 20)`).

| `GET /items?limit=50` | Requêtes `SELECT` |
|---|---|
| Avant | **4** : 1 pour la liste, puis 1 `SELECT ... FROM users WHERE users.id = ...` par propriétaire |
| Après `selectinload(Item.owner)` | **2** : la liste, puis 1 seul `SELECT ... FROM users WHERE users.id IN (...)` |

**D'où vient le N+1 :** aucune boucle dans notre code. C'est le `response_model=list[ItemRead]` de
la route : en sérialisant chaque item, Pydantic lit `item.owner`, et SQLAlchemy charge la relation
paresseusement, une requête par propriétaire. Il n'y en a que 3 et non 23 parce que la session
garde en mémoire les utilisateurs déjà chargés : le coût est de 1 + (nombre de propriétaires
distincts de la page), soit jusqu'à 51 requêtes pour une page de 50 items de 50 propriétaires.

**Correction** dans `ItemRepository.list` :
`select(Item).options(selectinload(Item.owner))`. Le nombre de requêtes est désormais constant
(2), quelle que soit la taille de la page.

`SQL_ECHO` remis à `false` après la mesure.

## Étape 6.4 — Modifications imposées au frontend par le contrat de l'API

| Changement de contrat (backend) | Effet constaté | Modification dans `frontend/` |
|---|---|---|
| `tarif_jour` devient un `Numeric` (`Decimal`), sérialisé en chaîne : `"5.00"` au lieu de `5.0` | La liste et le détail affichent `5.00 €` au lieu de `5.0 €` | Aucune : l'affichage est même plus juste pour un montant |
| `POST /items` exige un `owner_id` (un item a désormais un propriétaire) | La création affiche proprement l'erreur `422` du backend : « owner_id : Field required » | `routers/items.py` : `owner_id` fixé à `1` (utilisateur de démonstration inséré en base), marqué `# TODO séance 5` |
| `GET /items` renvoie un champ `owner` en plus (étape 5) | Rien : le frontend ignore les champs qu'il n'utilise pas | Aucune |
| `POST /reservations` exige un `borrower_id` (étape 7) | La réservation renverrait un `422` | `api_client.create_reservation` reçoit `borrower_id` ; `routers/reservations.py` le fixe à `1`, marqué `# TODO séance 5` |
| `POST /reservations` renvoie `409` (item indisponible, créneau pris) (étape 7) | Déjà géré : `MESSAGES_RESERVATION` du TP 1 traduit le `409` en « Ce créneau n'est pas disponible. » sur le formulaire | Aucune |

La liste et le détail ont fonctionné sans aucune modification : le contrat de lecture n'a pas
changé. Après `docker compose restart`, les items sont toujours là.
