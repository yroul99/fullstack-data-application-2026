# Étape 4 — Transactions

## Isolation

Requête relue des deux côtés : `SELECT tarif_jour FROM items WHERE id = 1;`

| Moment | Ce que voit A | Ce que voit B |
|---|---|---|
| A : `BEGIN` + `UPDATE ... 99.00`, non validé | 99.00 | 8.50 |
| A : `ROLLBACK` | 8.50 | 8.50 |
| A : `BEGIN` + `UPDATE ... 99.00`, non validé | 99.00 | 8.50 |
| A : `COMMIT` | 99.00 | 99.00 |

B ne voit jamais une modification non validée : il ne la voit qu'après le `COMMIT`, et jamais si A
annule.

## Atomicité

```sql
BEGIN;
INSERT INTO reservations (item_id, borrower_id, date_debut, date_fin) VALUES (1, 3, '2026-11-01', '2026-11-04');
UPDATE items SET disponible = FALSE WHERE id = 1;
INSERT INTO reservations (item_id, borrower_id, date_debut, date_fin) VALUES (1, 999, '2026-11-01', '2026-11-04');
-- ERROR:  insert or update on table "reservations" violates foreign key constraint "reservations_borrower_id_fkey"
COMMIT;
-- ROLLBACK
```

- La réservation de novembre **n'existe pas** (`0 rows`).
- Le vélo est **toujours disponible** (`disponible = t`).
- À la validation, `psql` répond **`ROLLBACK`** et non `COMMIT` : la transaction en erreur est
  entièrement annulée, y compris les deux instructions qui avaient réussi.
- Si on tape une autre commande entre l'erreur et la validation, elle est refusée :
  `ERROR:  current transaction is aborted, commands ignored until end of transaction block`.
  Toute commande est ignorée jusqu'au `COMMIT` / `ROLLBACK`, qui répond `ROLLBACK`.
