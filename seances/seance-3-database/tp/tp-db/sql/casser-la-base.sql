-- Étape 2 — Essayer de casser la base (les cinq doivent échouer)

-- 1. Deuxième utilisateur avec l'email alice@esiee.fr
INSERT INTO users (email, password_hash, display_name) VALUES ('alice@esiee.fr', 'x', 'Alice bis');
-- ERROR:  duplicate key value violates unique constraint "users_email_key"
-- DETAIL:  Key (email)=(alice@esiee.fr) already exists.

-- 2. Item dont le propriétaire n'existe pas
INSERT INTO items (owner_id, titre, tarif_jour) VALUES (999, 'Fantôme', 10.00);
-- ERROR:  insert or update on table "items" violates foreign key constraint "items_owner_id_fkey"
-- DETAIL:  Key (owner_id)=(999) is not present in table "users".

-- 3. Item à tarif négatif
INSERT INTO items (owner_id, titre, tarif_jour) VALUES (1, 'Tarif négatif', -5.00);
-- ERROR:  new row for relation "items" violates check constraint "items_tarif_jour_check"

-- 4. Réservation qui se termine avant de commencer
INSERT INTO reservations (item_id, borrower_id, date_debut, date_fin) VALUES (1, 3, '2026-10-10', '2026-10-05');
-- ERROR:  new row for relation "reservations" violates check constraint "dates_coherentes"

-- 5. Statut fantaisiste
INSERT INTO reservations (item_id, borrower_id, date_debut, date_fin, statut) VALUES (1, 3, '2026-10-10', '2026-10-15', 'en_attente_peut_etre');
-- ERROR:  new row for relation "reservations" violates check constraint "statut_valide"

-- Contraintes à intercepter en Python (séance 4) :
--   users_email_key, items_owner_id_fkey, items_tarif_jour_check, dates_coherentes, statut_valide


-- Suppression de Bob
SELECT count(*) FROM items WHERE owner_id = 2;
-- 2
DELETE FROM users WHERE id = 2;
-- ERROR:  update or delete on table "users" violates foreign key constraint "reservations_borrower_id_fkey" on table "reservations"
-- DETAIL:  Key (id)=(2) is still referenced from table "reservations".
-- Bob est emprunteur de la réservation 1 : la suppression est refusée. Rien n'est supprimé,
-- ses 2 items sont toujours là.


-- Sans ce garde-fou : on recrée la clé étrangère avec ON DELETE CASCADE
ALTER TABLE reservations DROP CONSTRAINT reservations_borrower_id_fkey;
ALTER TABLE reservations ADD CONSTRAINT reservations_borrower_id_fkey
    FOREIGN KEY (borrower_id) REFERENCES users(id) ON DELETE CASCADE;

DELETE FROM users WHERE id = 2;
-- DELETE 1
SELECT count(*) FROM items WHERE owner_id = 2;
-- 0
SELECT * FROM reservations;
-- (0 rows)
--
-- Les trois réservations ont disparu :
--   - réservation 1 (Vélo de ville d'Alice, empruntée par Bob) : perdue par Alice, propriétaire.
--     Cascade par reservations_borrower_id_fkey (Bob était l'emprunteur).
--   - réservation 2 (Tente 2 places de Bob, empruntée par Alice) : perdue par Alice, emprunteuse.
--     Cascade items_owner_id_fkey (la tente est supprimée) puis reservations_item_id_fkey.
--   - réservation 3 (Appareil photo de Bob, emprunté par Chloé) : perdue par Chloé, emprunteuse.
--     Même chemin : items_owner_id_fkey puis reservations_item_id_fkey.
