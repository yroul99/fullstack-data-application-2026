-- Données valides de départ
INSERT INTO avis (reservation_id, note, commentaire) VALUES (1, 5, 'Vélo impeccable');
INSERT INTO tags (libelle) VALUES ('velo');

-- Les insertions suivantes doivent toutes échouer

-- 1. Note à 6
INSERT INTO avis (reservation_id, note) VALUES (2, 6);
-- ERROR:  new row for relation "avis" violates check constraint "avis_note_valide"

-- 2. Deux avis sur la même réservation
INSERT INTO avis (reservation_id, note) VALUES (1, 3);
-- ERROR:  duplicate key value violates unique constraint "avis_reservation_unique"

-- 3. Deux tags de même libellé
INSERT INTO tags (libelle) VALUES ('velo');
-- ERROR:  duplicate key value violates unique constraint "tags_libelle_unique"

-- 4. Un avis sur une réservation inexistante
INSERT INTO avis (reservation_id, note) VALUES (999, 4);
-- ERROR:  insert or update on table "avis" violates foreign key constraint "avis_reservation_fk"

-- 5. Deux réservations actives qui se chevauchent sur le même item
--    (la Tente 2 places est déjà réservée du 2026-09-10 au 2026-09-12)
INSERT INTO reservations (item_id, borrower_id, date_debut, date_fin) VALUES (3, 3, '2026-09-11', '2026-09-14');
-- ERROR:  conflicting key value violates exclusion constraint "reservations_sans_chevauchement"
