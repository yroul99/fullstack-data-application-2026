# Sécurité — authentification et autorisation (séance 5)

## Règles d'autorisation

| Action | Qui a le droit | Sinon |
|---|---|---|
| Lister / consulter le matériel | Tout le monde | — |
| Publier du matériel | Utilisateur authentifié ; le propriétaire est l'auteur du jeton | `401` |
| Modifier / remplacer / supprimer un matériel | Son propriétaire uniquement | `401` / `403` |
| Réserver un matériel | Utilisateur authentifié, **sauf** le propriétaire lui-même ; l'emprunteur est l'auteur du jeton | `401` / `409` |
| Lister / consulter les réservations | Utilisateur authentifié | `401` |
| Annuler une réservation | L'emprunteur ou le propriétaire du matériel | `401` / `403` |
| `GET /auth/me` | Utilisateur authentifié | `401` |

Chaque ligne est couverte par trois tests (anonyme, propriétaire, autre utilisateur) dans
`backend/tests/test_autorisation.py`. Vérifié : en retirant `CurrentUser` de
`DELETE /items/{id}`, deux tests échouent (l'anonyme et Bob obtiennent `204`).

## Décisions

- **`403` plutôt que `404`** quand un utilisateur agit sur le matériel d'un autre : le catalogue
  est public, l'existence de l'item n'est pas une information à cacher.
- **Durée de vie du jeton : 60 minutes, sans refresh token.** Un JWT ne se révoque pas : un jeton
  volé reste valable jusqu'à son `exp`, et la déconnexion ne supprime que le cookie. Une durée
  courte limite cette fenêtre ; la solution complète (jeton d'accès de 15 min + refresh token
  révocable en base) n'est pas mise en place.
- **`owner_id` envoyé dans le corps** : les schémas de création refusent les champs inconnus
  depuis la séance 1 (`extra="forbid"`), donc `POST /items` avec un `owner_id` répond `422` au lieu
  d'ignorer le champ. Aucune usurpation possible dans les deux cas ; le test vérifie le `422` et
  qu'aucun item n'a été créé au nom de Bob.
- **Même `401` quelle que soit la cause** : `OAuth2PasswordBearer(auto_error=False)`, pour que
  l'absence de jeton renvoie le même corps (`"Identifiants invalides"`) que le jeton malformé,
  expiré ou d'un utilisateur supprimé, au lieu du `"Not authenticated"` de FastAPI.
- **Côté frontend**, un visiteur sans cookie ne charge pas les réservations d'un item (route
  authentifiée) : la page de détail l'invite à se connecter au lieu de le rediriger.

## Tests depuis un clone propre

La base `gearshare_test` est créée par `db/init/01-base-de-test.sql`, monté sur
`/docker-entrypoint-initdb.d` du service `db` (mécanisme de la séance 3) : après `git clone`,
`cp .env.example .env` et `docker compose up`, `docker compose run --rm backend pytest` passe
sans autre commande (vérifié après `docker compose down -v` : 129 tests).

## Expériences de l'étape 8

| Expérience | Résultat |
|---|---|
| 8.1 — `JWT_SECRET=secret`, jeton d'Alice re-signé avec `sub` = id de Bob | `GET /auth/me` → `200` **Bob**. Avec un secret faible ou commité, n'importe qui se fait passer pour n'importe qui. Remis le vrai secret : le même jeton forgé → `401` |
| 8.2 — `JWT_EXPIRE_MINUTES=1`, attente de 65 s | `GET /auth/me` → `401` ; la page de détail renvoie vers `/connexion?suivant=/items/3` et supprime le cookie |
| 8.3 — Carol supprimée en base, ancien jeton | `GET /auth/me` → `401` (`get_current_user` relit l'utilisateur en base) |

## Relecture finale (étape 9)

| Point | |
|---|---|
| `JWT_SECRET` hors du code, 32 octets aléatoires ou plus | OK (`openssl rand -hex 32`, dans `.env`) |
| `.env` absent du dépôt **et de l'historique** | OK (`git log --all -- .env` ne renvoie rien) |
| Le frontend ne reçoit pas `JWT_SECRET` | OK (`docker compose exec frontend env \| grep -i jwt` : rien) |
| PBKDF2-HMAC-SHA256, 600 000 itérations, sel tiré par `secrets` | OK |
| Comparaison en temps constant | OK (`hmac.compare_digest`) |
| `password_hash` absent des schémas de lecture | OK (`UserRead`, `OwnerRead`) |
| Payload limité à `sub`, `iat`, `exp` | OK |
| `exp` présent et vérifié | OK (vérifié par `jwt.decode`, expérience 8.2) |
| Liste explicite d'algorithmes au décodage | OK (`algorithms=["HS256"]`) |
| `get_current_user` relit l'utilisateur en base | OK (expérience 8.3) |
| Même `401` quelle que soit la cause, avec `WWW-Authenticate` | OK (testé) |
| Toutes les routes d'écriture protégées | OK |
| L'identité vient du jeton, jamais du corps | OK (`owner_id` et `borrower_id` retirés des schémas) |
| Propriété vérifiée dans le service, `403` | OK (`ItemService`, `ReservationService`) |
| Message de login identique (email inconnu / mauvais mot de passe) | OK (testé) |
| Longueur min. et max. du mot de passe | OK (12–128) |
| Aucun mot de passe dans les logs | OK (aucune occurrence dans `docker compose logs`) |
| Jeton passé en paramètre au client d'API | OK |
| Cookie `HttpOnly`, `SameSite=Lax`, `Secure` configurable | OK (`COOKIE_SECURE`) |
| Aucune modification par `GET`, déconnexion comprise | OK (`GET /deconnexion` → `405`) |
| Paramètre `suivant` limité aux pages du site | OK (`https://…`, `//…`, `/\…` → `/items`) |

**Recherche de secrets** (`git grep -niE "secret|password|token"`) : les lignes restantes sont
toutes des noms (paramètres `token` / `password`, `jwt_secret` lu depuis la configuration, module
`secrets`, `${POSTGRES_PASSWORD}` substitué depuis le `.env`) ou les mots de passe factices des
tests. Aucune valeur secrète réelle n'est dans le code.
