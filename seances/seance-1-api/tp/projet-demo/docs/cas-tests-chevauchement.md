# Cas de tests — chevauchement de réservations

## La condition

Il n'y a **pas** de conflit dans deux cas seulement : la réservation existante finit avant le début
demandé, ou elle commence après la fin demandée. Le conflit est la négation de « fin existante ≤
début demandé OU début existant ≥ fin demandée », soit :

```text
existante.date_debut < fin_demandee  ET  existante.date_fin > debut_demandee
```

(sur les réservations **actives** du même item), dans `ReservationRepository.find_chevauchements`.

**Décision sur les réservations jointives :** elles ne sont **pas** en conflit. Une réservation qui
finit le 5 libère le matériel le 5, une autre peut commencer le 5. Les inégalités strictes (`<`,
`>`) traduisent cette décision ; passer à `<=` / `>=` la changerait.

## Les cas

Réservation existante : item 1, **du 2026-09-01 au 2026-09-05**, statut `active`.
Rejoués avec `curl` sur `POST /reservations` ; chaque réservation acceptée est annulée aussitôt
pour ne pas fausser le cas suivant.

| Cas | Créneau demandé | Code attendu | Code obtenu |
|---|---|---|---|
| Avant | 2026-08-28 → 2026-08-31 | `201` | `201` |
| Après | 2026-09-06 → 2026-09-08 | `201` | `201` |
| Chevauchement partiel au début | 2026-08-30 → 2026-09-03 | `409` | `409` « Ce créneau est déjà réservé » |
| Chevauchement partiel à la fin | 2026-09-03 → 2026-09-08 | `409` | `409` « Ce créneau est déjà réservé » |
| Englobant | 2026-08-30 → 2026-09-10 | `409` | `409` « Ce créneau est déjà réservé » |
| Inclus (bonus) | 2026-09-02 → 2026-09-04 | `409` | `409` « Ce créneau est déjà réservé » |
| Jointif après (commence le jour où l'autre finit) | 2026-09-05 → 2026-09-08 | `201` | `201` |
| Jointif avant (finit le jour où l'autre commence) | 2026-08-28 → 2026-09-01 | `201` | `201` |

## Les autres codes du contrat

| Cas | Code attendu | Code obtenu |
|---|---|---|
| `POST` sur un item inexistant (`item_id: 999`) | `404` | `404` « Item 999 introuvable » |
| `POST` avec un emprunteur inexistant (`borrower_id: 999`) | `404` | `404` « Utilisateur 999 introuvable » |
| `POST` avec `date_fin` avant `date_debut` | `422` | `422` |
| `POST` sur un item `disponible = false` | `409` | `409` « Ce matériel n'est pas disponible » |
| `GET /reservations?item_id=1&limit=2` | `200` | `200`, 2 réservations |
| `GET /reservations/999` | `404` | `404` |
| `PATCH /reservations/1` `{"statut": "annulee"}` | `200` | `200`, statut `annulee` |
| Le même `PATCH` une seconde fois | `409` | `409` « Seule une réservation active peut être annulée » |
| `PATCH /reservations/999` | `404` | `404` |
| `PATCH` avec `{"statut": "active"}` | `422` | `422` |
