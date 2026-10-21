# Review de la verticale `reservations`

Relue à froid, fichier par fichier : `models/reservation.py`, `schemas/reservation.py`,
`repositories/reservation.py`, `services/reservation.py`, `routers/reservations.py`,
`api/deps.py`.

| Point de contrôle | OK / KO | Ce que j'ai corrigé |
|---|---|---|
| Aucun SQL ni requête SQLAlchemy dans le router | OK | — |
| Aucune `HTTPException` dans le service (uniquement les exceptions métier) | OK | L'ancien router en mémoire levait des `HTTPException` et une `ReservationConflict` propre aux réservations : remplacées par `RessourceIntrouvable` / `ConflitReservation`, traduites par le gestionnaire global. `app/exceptions.py` supprimé |
| Aucun `commit()` dans le repository | OK | — (`flush()` seulement ; la transaction est validée par `get_db`) |
| `response_model` sur les 4 routes | OK | — |
| Schéma de lecture construit depuis l'objet SQLAlchemy, sans champ interne | OK | `ReservationRead` a `from_attributes=True` ; son `statut` accepte maintenant aussi `terminee`, autorisé par la contrainte `statut_valide` |
| La requête de chevauchement couvre les cinq cas, y compris l'englobant | OK | — (vérifié : voir `docs/cas-tests-chevauchement.md`) |
| Pas de f-string dans une requête SQL | OK | — |
| Pas de N+1 sur `GET /reservations` (si la relation `item` est chargée) | OK | `ReservationRead` ne contient que des colonnes (`item_id`, `borrower_id`), aucune relation n'est chargée : une seule requête |
| Migration relue, `downgrade()` testé | OK | Le modèle `Reservation` n'a pas changé depuis la migration initiale (`alembic check` : « No new upgrade operations detected ») ; son `downgrade()` a été testé à l'étape 3 |
| Aucune dépendance ajoutée sans justification | OK | Aucune dépendance de plus que les quatre de l'étape 0 |

## Corrections faites pendant la review

- **Méthodes `list` renommées** en `list_items` / `list_reservations` dans les repositories et les
  services : une méthode nommée `list` masque le type `list` dans le reste du corps de la classe,
  et l'annotation `-> list[Reservation]` de `find_chevauchements` faisait planter le démarrage
  (`TypeError: 'function' object is not subscriptable`).
- **Emprunteur vérifié dans le service** : sans cette vérification, un `borrower_id` inexistant
  aurait été détecté par la clé étrangère et renvoyé en `500` (même problème que pour
  `owner_id` à l'étape 4).

## Changement de contrat

`POST /reservations` exige désormais un `borrower_id` : la colonne est obligatoire en base, et
l'emprunteur ne peut pas encore être déduit d'un jeton. Provisoire jusqu'à la séance 5.
