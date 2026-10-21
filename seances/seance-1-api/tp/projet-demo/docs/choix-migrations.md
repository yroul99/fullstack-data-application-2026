# Choix : comment appliquer les migrations au démarrage

## Les quatre questions

**1. Que se passe-t-il au deuxième `docker compose up`, quand la base est déjà à jour ?**

`alembic upgrade head` relit la table `alembic_version`, constate que la base est déjà à la
révision `head` et ne fait rien. Constaté avec le service `migrate` : ses logs n'affichent que
`Context impl PostgresqlImpl` / `Will assume transactional DDL`, sans aucune ligne
`Running upgrade`, il sort en `Exited (0)` et le backend démarre normalement. C'est pareil avec un
`entrypoint.sh` : la commande est sans effet, elle coûte seulement une connexion à la base à chaque
démarrage du backend.

**2. Si une migration échoue, que voit-on dans `docker compose ps` et dans les logs ? Le backend
démarre-t-il quand même ?**

Testé avec une migration volontairement cassée (`SELECT` sur une table inexistante) :

- `docker compose up` affiche `service "migrate" didn't complete successfully: exit 1` ;
- `docker compose ps -a` montre `migrate: Exited (1)` et `backend: Created` : **le backend ne
  démarre pas** ;
- `docker compose logs migrate` donne la cause exacte :
  `psycopg.errors.UndefinedTable: relation "table_qui_n_existe_pas" does not exist`.

La migration étant transactionnelle, la base reste à la révision précédente. Avec un
`entrypoint.sh` (`set -e`), le conteneur backend s'arrêterait aussi, mais l'erreur serait
mélangée aux logs de l'API, et un `restart:` relancerait la migration en boucle.

**3. En production, que se passerait-il si trois instances du backend démarraient en même temps
sur une base pas encore migrée ?**

Avec un `entrypoint.sh`, les trois instances lanceraient `alembic upgrade head` en même temps sur
la même base : elles essaieraient toutes de créer les mêmes tables et d'écrire la même ligne dans
`alembic_version`. Au mieux, deux échouent et redémarrent ; au pire, une migration non
transactionnelle (ou une migration de données) est appliquée partiellement deux fois. Avec un
service `migrate` exécuté **une fois**, avant que les instances ne démarrent, la question ne se
pose pas : les instances du backend ne migrent jamais.

**4. Le backend tourne en `--reload` : l'option fonctionne-t-elle toujours ?**

Oui avec le service `migrate` : le backend garde sa commande
`uvicorn ... --reload` dans le `docker-compose.yml`, rien ne change pour lui. Avec un
`entrypoint.sh` qui se termine par `exec uvicorn ...` en dur, le `command:` de Compose ne serait plus
utilisé et le `--reload` serait perdu (il faudrait que le script se termine par `exec "$@"`).
À noter dans les deux cas : `--reload` recharge le code Python, pas les migrations. Une nouvelle
migration en développement demande de relancer `migrate` (`docker compose up -d`) ou
`docker compose run --rm backend alembic upgrade head`.

## Notre choix : le service `migrate` (option 2)

- **Responsabilités séparées** : la migration a son propre conteneur, son propre statut
  (`Exited (0)` / `Exited (1)`) et ses propres logs, lisibles indépendamment de l'API.
- **Un échec bloque le démarrage proprement** : grâce à
  `condition: service_completed_successfully`, le backend ne sert jamais une requête sur un schéma
  pas à jour.
- **Pas de migrations concurrentes** quand on multiplie les instances du backend.
- **Rien à changer côté backend** : même image, même commande, `--reload` conservé.

Le coût est un service de plus dans le `docker-compose.yml`, construit depuis la même image.
