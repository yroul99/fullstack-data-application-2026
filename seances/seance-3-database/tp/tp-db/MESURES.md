# Étape 5 — Index et `EXPLAIN ANALYZE`

Volume généré (200 000 items d'Alice, tarif aléatoire entre 1 et 51 €) :

```sql
INSERT INTO items (owner_id, titre, tarif_jour)
SELECT 1, 'Item de test ' || n, round((1 + random() * 50)::numeric, 2)
FROM generate_series(1, 200000) AS n;
ANALYZE items;
```

## Recherche par titre exact

```sql
EXPLAIN ANALYZE SELECT * FROM items WHERE titre = 'Item de test 123456';
```

| | Nœud | Execution Time |
|---|---|---|
| Sans index | `Seq Scan on items` (`Rows Removed by Filter: 200003`) | 31.359 ms |
| Avec `CREATE INDEX idx_items_titre ON items (titre);` | `Index Scan using idx_items_titre` | 0.059 ms |

**Facteur d'accélération : ≈ 530** (31.359 / 0.059).

## Cas plus subtils

**(a) Titres qui se terminent par `123456`** : `WHERE titre LIKE '%123456'`
→ `Seq Scan`, 34.894 ms, malgré l'index sur `titre`.

Un B-tree est trié par le début de la chaîne : avec un joker en tête, on ne connaît pas le début,
donc l'index ne permet pas de savoir où chercher et il faut lire toute la table.

**(b) Filtre sur `disponible`**, après `CREATE INDEX idx_items_disponible ON items (disponible);`
et `ANALYZE` :

| Requête | Lignes concernées | Nœud | Execution Time |
|---|---|---|---|
| `disponible = TRUE` | 200 004 (toute la table) | `Seq Scan` | 34.522 ms |
| `disponible = FALSE` | 0 | `Index Scan using idx_items_disponible` | 0.059 ms |

Toutes les lignes valent `TRUE` : pour `TRUE`, l'index ne filtre rien et le planificateur préfère
lire la table directement, alors que pour `FALSE` (aucune ligne) l'index est très sélectif et il
s'en sert.

**Bonus : joker en fin**, `WHERE titre LIKE 'Item de test 12345%'`
→ `Seq Scan`, 27.068 ms : **non**, l'index sur `titre` ne sert pas ici.

La base est en collation `en_US.utf8` : un B-tree ordinaire trie selon cette collation, que
PostgreSQL ne peut pas utiliser pour un `LIKE` par préfixe (il faudrait un index créé avec
`varchar_pattern_ops`, ou une base en collation `C`).
