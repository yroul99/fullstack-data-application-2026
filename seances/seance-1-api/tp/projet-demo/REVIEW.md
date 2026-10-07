# Review — ressource `reservations` générée par Copilot

Code généré par Copilot (mode Plan puis Agent) à partir de `SPEC-reservations.md` et
`app/routers/items.py`. Chaque point a été vérifié en appelant l'API, pas seulement en lisant le code.

## Grille

| Point de contrôle | OK / KO | Ce que j'ai corrigé |
|---|---|---|
| Les codes de statut correspondent à la spec (201, 404, 409) | OK | Rien. Testé : `POST` valide → 201, `GET /reservations/999` → 404, double annulation → 409 `"Reservation déjà annulée"`, `date_fin <= date_debut` → 422, `limit=500` → 422. |
| `response_model` présent sur les 4 routes | OK | Rien. `list[ReservationRead]` sur la liste, `ReservationRead` sur les trois autres. |
| La validation `date_fin > date_debut` est bien dans le schéma Pydantic | OK | Rien. Copilot a utilisé un `@model_validator(mode="after")` dans `ReservationCreate`, la bonne réponse pour une validation croisée entre deux champs (impossible avec `Field`). Le cas `date_fin == date_debut` est bien refusé (`<=`). |
| Le router n'accède pas au stockage de `items` | OK | Rien : aucun import de `app.routers.items`. Conséquence assumée de la spec : on peut réserver un item inexistant (`item_id: 999` → 201). Voir « Limites ». |
| Pas d'`async def` sans `await` | OK | Rien : toutes les routes sont en `def` synchrone. |
| Aucune dépendance ajoutée dans `requirements.txt` (ou justifiée) | OK | Rien : fichier inchangé. `datetime.date` et `typing.Literal` sont dans la bibliothèque standard. |
| Les routes littérales sont déclarées avant les routes paramétrées | OK | Rien. `GET ""` est déclaré avant `GET "/{reservation_id}"` ; `/{reservation_id}/annuler` n'entre en conflit avec aucune autre route. |
| Le code renvoie une réponse cohérente pour `POST /reservations/999/annuler` | OK | Rien : 404 `"Reservation 999 introuvable"` (la vérification d'existence passe avant celle du statut). `POST /reservations/abc/annuler` → 422. |

## Problèmes trouvés hors grille

| Problème | Gravité | Correction |
|---|---|---|
| **Copilot a travaillé dans un worktree séparé** (`copilot-worktrees/.../yroul99-urban-pancake`), créé depuis un ancien commit où `items` n'existait pas. Son `main.py` n'incluait que `reservations` : intégré tel quel, il **supprimait toutes les routes `/items`** et remettait `/health` à sa version d'origine. Son résumé (« validation passed ») ne le signalait pas. | Haute | `main.py` fusionné à la main : `app.include_router(items.router)` **et** `app.include_router(reservations.router)`. |
| `ReservationCreate` acceptait des champs inconnus en silence : `{"...", "statut": "annulee"}` → 201 avec `statut: "active"`. Le client croit avoir fixé un statut qui a été ignoré. Incohérent avec `ItemCreate`. | Moyenne | Ajout de `model_config = ConfigDict(extra="forbid")` → 422. |
| Ligne de compréhension de liste de 104 caractères dans `list_reservations`. | Style | Renommée `r`, sur une ligne courte. |

## Limites (hors périmètre de la spec, non corrigées)

- **Item inexistant** : la contrainte « aucun accès à FAKE_DB de items » empêche de vérifier que `item_id` existe. Avec une vraie base, ce serait une clé étrangère (→ 404 ou 422).
- **Chevauchement** : deux réservations actives peuvent porter sur le même item aux mêmes dates. Ce serait un 409 métier, que la spec ne demande pas.
- **Dates passées** : rien n'interdit une réservation dont `date_debut` est dans le passé.
- Le `if statut == "annulee"` → 409 reste dans le router : c'est une règle qui dépend de l'état stocké, pas des données reçues, donc elle ne peut pas vivre dans Pydantic. Ça respecte la contrainte « tout ce qui **peut** l'être ».

## Bilan

Le code métier produit par Copilot était correct du premier coup sur les 8 points de la grille, y compris
la validation croisée. Le vrai défaut était **l'intégration** : un agent qui travaille sur une copie
périmée du dépôt peut livrer un code localement juste qui casse le reste de l'application. C'est
invisible si on lit seulement le diff du nouveau fichier ; il faut relancer l'API complète et vérifier
`/docs`.
