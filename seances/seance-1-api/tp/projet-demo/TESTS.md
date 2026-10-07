# Tests — séance 2

## Lancer la suite

```bash
docker compose build                     # après un changement de requirements.txt ou de Dockerfile
docker compose run --rm api pytest -v
docker compose run --rm api pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

## Organisation

| Fichier | Niveau | Contenu |
|---|---|---|
| `tests/conftest.py` | — | `Storage` + fixtures `storage`, `client` (dépend de `storage`), `item_velo`, `reservation_active` |
| `tests/test_health.py` | Intégration | Sonde `/health` |
| `tests/test_items.py` | Intégration | CRUD `items` : nominal, 422 paramétrés, 404 sur les 4 routes d'un item, filtres, `skip`/`limit`, `/items/search` |
| `tests/test_reservations.py` | Intégration | Création, liste, consultation, annulation (200 / 404 / 409), notification mockée |
| `tests/test_schemas.py` | Unitaire | `ReservationCreate` (dates, `extra="forbid"`), `ItemCreate`, `ItemUpdate` sans HTTP |

72 tests, couverture **99 %**. La seule ligne non couverte est le corps de
`envoyer_notification_annulation` : elle est toujours remplacée par un `Mock` dans les tests,
c'est voulu.

## Mock : la notification d'annulation

`POST /reservations/{id}/annuler` appelle `envoyer_notification_annulation(reservation_id=...)`,
seule dépendance externe du router. Les tests la remplacent par un `Mock` via `monkeypatch`
(fixture `notifier`) et vérifient :

- qu'elle est appelée une fois, avec le bon identifiant ;
- qu'elle n'est pas appelée sur un 404, ni rappelée sur un 409 ;
- **décision** : si elle lève une exception, l'annulation reste acquise (200, statut `annulee`).
  L'erreur est journalisée.

## Test de mutation

Chaque règle a été cassée volontairement dans le code, la suite relancée, puis le code restauré.

| Mutation introduite | Détectée | Tests passés au rouge |
|---|---|---|
| Suppression du `raise ReservationConflict` (double annulation) | ✅ | `test_annuler_une_reservation_deja_annulee_renvoie_409`, `test_double_annulation_ne_notifie_qu_une_fois` |
| `model_dump(exclude_unset=True)` → `model_dump()` dans le `PATCH` | ✅ | `test_modifier_un_seul_champ_laisse_les_autres_intacts`, `test_modifier_sans_champ_ne_change_rien` |
| Suppression de `extra="forbid"` dans `ItemCreate` | ✅ | `test_creation_item_invalide_renvoie_422[...-couleur]` |
| `date_fin <= date_debut` → `<` (dates égales acceptées) | ✅ | `test_creer_reservation_avec_dates_incoherentes_renvoie_422[egales]`, `test_dates_egales_sont_refusees_par_le_schema` |
| Le `try/except` de la notification ne rattrape plus l'erreur | ✅ | `test_annulation_reussit_meme_si_la_notification_echoue` |
| `skip` ignoré dans `GET /items` | ✅ | `test_lister_avec_skip_saute_les_premiers` |
| `PATCH` sur un item inexistant le crée au lieu de renvoyer 404 | ✅ | `test_route_sur_item_inexistant_renvoie_404[PATCH-...]` |

Le cas des dates **égales** est celui qui justifie le plus l'exercice : un test qui ne vérifierait
que des dates inversées resterait vert avec `<` au lieu de `<=`.

## Non testé (hors spec)

- Réservation d'un item inexistant : acceptée (201), voir `REVIEW.md`, « Limites ».
- Réservation dans le passé : aucune règle dans la spec, donc pas de `aujourd_hui()` à mocker.
