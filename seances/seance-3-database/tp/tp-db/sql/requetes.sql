-- 1. Les items disponibles à moins de 10 €/jour, triés par tarif croissant
SELECT id, titre, tarif_jour
FROM items
WHERE disponible = TRUE
  AND tarif_jour < 10
ORDER BY tarif_jour ASC;
--  id |     titre     | tarif_jour
-- ----+---------------+------------
--   2 | Perceuse      |       5.00
--   1 | Vélo de ville |       8.50
-- (2 rows)


-- 2. Les items dont le titre contient « velo », insensible à la casse
SELECT id, titre
FROM items
WHERE titre ILIKE '%velo%';
--  id | titre
-- ----+-------
-- (0 rows)
--
-- ILIKE est insensible à la casse, mais pas aux accents : « Vélo » contient « é », pas « e ».
-- Pour une recherche tolérante aux accents, il faudrait l'extension unaccent.


-- 3. Chaque item avec le nom de son propriétaire
SELECT i.id, i.titre, u.display_name AS proprietaire
FROM items AS i
JOIN users AS u ON u.id = i.owner_id;
--  id |     titre      | proprietaire
-- ----+----------------+--------------
--   1 | Vélo de ville  | Alice
--   2 | Perceuse       | Alice
--   3 | Tente 2 places | Bob
--   4 | Appareil photo | Bob
-- (4 rows)


-- 4. Le nombre de réservations par item, y compris les items jamais réservés
SELECT i.titre, COUNT(r.id) AS nb_reservations
FROM items AS i
LEFT JOIN reservations AS r ON r.item_id = i.id
GROUP BY i.id, i.titre
ORDER BY nb_reservations DESC;
--      titre      | nb_reservations
-- ----------------+-----------------
--  Tente 2 places |               1
--  Appareil photo |               1
--  Vélo de ville  |               1
--  Perceuse       |               0
-- (4 rows)
--
-- LEFT JOIN pour garder la Perceuse, et COUNT(r.id) (pas COUNT(*)) pour qu'elle compte 0 et non 1.


-- 5. Pour chaque utilisateur ayant publié au moins un item : nb d'items et tarif moyen
SELECT
    u.display_name,
    COUNT(i.id)                 AS nb_items,
    ROUND(AVG(i.tarif_jour), 2) AS tarif_moyen
FROM users AS u
LEFT JOIN items AS i ON i.owner_id = u.id
GROUP BY u.id, u.display_name
HAVING COUNT(i.id) > 0
ORDER BY nb_items DESC;
--  display_name | nb_items | tarif_moyen
-- --------------+----------+-------------
--  Bob          |        2 |       16.00
--  Alice        |        2 |        6.75
-- (2 rows)


-- 6. Les réservations actives qui commencent après le 1er septembre 2026,
--    avec le titre du matériel et le nom de l'emprunteur
SELECT r.id, i.titre, u.display_name AS emprunteur, r.date_debut, r.date_fin
FROM reservations AS r
JOIN items AS i ON i.id = r.item_id
JOIN users AS u ON u.id = r.borrower_id
WHERE r.statut = 'active'
  AND r.date_debut > '2026-09-01';
--  id |     titre      | emprunteur | date_debut |  date_fin
-- ----+----------------+------------+------------+------------
--   2 | Tente 2 places | Alice      | 2026-09-10 | 2026-09-12
--   3 | Appareil photo | Chloé      | 2026-09-15 | 2026-09-20
-- (2 rows)


-- 7. Les 2 items les plus chers, en sautant le premier
SELECT id, titre, tarif_jour
FROM items
ORDER BY tarif_jour DESC
LIMIT 2 OFFSET 1;
--  id |     titre      | tarif_jour
-- ----+----------------+------------
--   3 | Tente 2 places |      12.00
--   1 | Vélo de ville  |       8.50
-- (2 rows)


-- 8. Le chiffre d'affaires potentiel de chaque réservation active
SELECT
    r.id,
    i.titre,
    i.tarif_jour,
    r.date_fin - r.date_debut                AS nb_jours,
    i.tarif_jour * (r.date_fin - r.date_debut) AS ca_potentiel
FROM reservations AS r
JOIN items AS i ON i.id = r.item_id
WHERE r.statut = 'active';
--  id |     titre      | tarif_jour | nb_jours | ca_potentiel
-- ----+----------------+------------+----------+--------------
--   2 | Tente 2 places |      12.00 |        2 |        24.00
--   3 | Appareil photo |      20.00 |        5 |       100.00
-- (2 rows)
