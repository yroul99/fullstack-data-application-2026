# Review du schéma v2 (`sql/init/03-schema-v2.sql`)

## Règles métier → mécanisme

| Règle | Mécanisme |
|---|---|
| 1. Note entière de 1 à 5, commentaire optionnel | `SMALLINT NOT NULL` + `CHECK avis_note_valide`, `commentaire TEXT` nullable |
| 1. Avis seulement par l'emprunteur, après une réservation `terminee` | **Rien côté base** : la condition porte sur une autre table (`reservations`), un `CHECK` ne peut pas la vérifier. Gérée en applicatif |
| 2. Un avis ↔ exactement une réservation, un seul avis par réservation | `reservation_id NOT NULL` + clé étrangère `avis_reservation_fk` + `UNIQUE avis_reservation_unique` |
| 3. Tags N–N, libellé unique en minuscules | Table `tags` (`UNIQUE tags_libelle_unique`, `CHECK tags_libelle_minuscules`) + table de liaison `item_tags` à clé primaire composite |
| 4. Pas deux réservations actives qui se chevauchent sur un item | Contrainte d'exclusion `reservations_sans_chevauchement` (extension `btree_gist`) |

## Grille

| Point de contrôle | OK / KO | Ce que j'ai corrigé |
|---|---|---|
| Chaque table a une clé primaire | OK | — |
| Les clés étrangères sont déclarées avec `REFERENCES` | OK | — |
| Les `ON DELETE` sont explicites et cohérents avec le métier | OK | `avis` → `CASCADE` (un avis n'a pas de sens sans sa réservation) ; `item_tags` → `CASCADE` des deux côtés (on supprime le lien, pas l'item ni le tag) |
| La règle « un seul avis par réservation » est garantie par une contrainte `UNIQUE` | OK | — |
| La note est bornée par un `CHECK (note BETWEEN 1 AND 5)` | OK | — |
| La table de liaison item/tag a une clé primaire composite | OK | — |
| Le libellé de tag est `UNIQUE` | OK | — |
| Les contraintes sont nommées | OK | — |
| Des index existent sur les clés étrangères | OK | `items.owner_id`, `reservations.item_id`, `reservations.borrower_id`, `item_tags.tag_id`. `avis.reservation_id` est couvert par le `UNIQUE`, `item_tags.item_id` par la clé primaire (première colonne) |
| Le non-chevauchement est réellement garanti (contrainte) ou explicitement laissé à l'applicatif | OK | Garanti par `EXCLUDE USING gist (item_id WITH =, daterange(date_debut, date_fin) WITH &&) WHERE (statut = 'active')`. Les réservations annulées ou terminées ne bloquent pas |
| Aucun type flottant pour un montant, aucun `TIMESTAMP` sans fuseau | OK | — |

Preuve : `sql/tests-contraintes.sql`, où les cinq insertions échouent chacune sur la contrainte
attendue.

## Suppression d'un utilisateur (question de l'étape 2)

Avec `ON DELETE CASCADE` sur `borrower_id`, supprimer Bob a effacé les trois réservations,
y compris l'historique d'Alice et de Chloé, qui n'avaient rien demandé.

Décision pour GearShare : **on garde le comportement par défaut (`RESTRICT`) sur `borrower_id`**.
La suppression d'un compte qui a des emprunts est refusée, ce qui préserve l'historique des prêts
faits sur le matériel des autres. Pour supprimer un compte, l'application devra d'abord traiter ces
réservations explicitement (par exemple anonymiser ou désactiver le compte plutôt que le supprimer).
