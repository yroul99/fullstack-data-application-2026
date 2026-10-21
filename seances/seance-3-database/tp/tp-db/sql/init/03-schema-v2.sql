-- Règles 1 et 2 : un avis par réservation, note de 1 à 5, commentaire optionnel
CREATE TABLE avis (
    id             BIGSERIAL PRIMARY KEY,
    reservation_id BIGINT      NOT NULL,
    note           SMALLINT    NOT NULL,
    commentaire    TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT avis_reservation_fk     FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE,
    CONSTRAINT avis_reservation_unique UNIQUE (reservation_id),
    CONSTRAINT avis_note_valide        CHECK (note BETWEEN 1 AND 5)
);
-- « L'avis est laissé par l'emprunteur, après une réservation terminee » porte sur une autre
-- table : un CHECK ne peut pas le garantir. Vérifié côté applicatif (voir REVIEW-schema.md).

-- Règle 3 : tags, relation N-N avec les items
CREATE TABLE tags (
    id      BIGSERIAL PRIMARY KEY,
    libelle VARCHAR(50) NOT NULL,
    CONSTRAINT tags_libelle_unique     UNIQUE (libelle),
    CONSTRAINT tags_libelle_minuscules CHECK (libelle = lower(libelle))
);

CREATE TABLE item_tags (
    item_id BIGINT NOT NULL,
    tag_id  BIGINT NOT NULL,
    CONSTRAINT item_tags_pk      PRIMARY KEY (item_id, tag_id),
    CONSTRAINT item_tags_item_fk FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    CONSTRAINT item_tags_tag_fk  FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
);

-- Règle 4 : pas deux réservations actives qui se chevauchent sur un même item
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE reservations
    ADD CONSTRAINT reservations_sans_chevauchement
    EXCLUDE USING gist (item_id WITH =, daterange(date_debut, date_fin) WITH &&)
    WHERE (statut = 'active');

-- Index sur les clés étrangères (PostgreSQL ne les crée pas automatiquement)
CREATE INDEX idx_items_owner           ON items (owner_id);
CREATE INDEX idx_reservations_item     ON reservations (item_id);
CREATE INDEX idx_reservations_borrower ON reservations (borrower_id);
CREATE INDEX idx_item_tags_tag         ON item_tags (tag_id);
-- avis.reservation_id : déjà indexé par la contrainte UNIQUE.
-- item_tags.item_id : déjà indexé, première colonne de la clé primaire composite.
