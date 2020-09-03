# Development

## Requirements
- Python 3.8.x
- [poetry](https://python-poetry.org/)
- [PostgreSQL](https://www.postgresql.org/) (tested on 12.2)

All the Python-specific details are in the `pyproject.toml` file, but this is something
that poetry takes care of -- there's no need to install anything manually.


## Set up instructions
1. Clone the repo: `git clone git@git.blender.org:blender-studio.git`
2. Checkout the develop branch (master may be considerably outdated):
    `git checkout develop`
2. Run `poetry install`
   - if the installation of psycopg2 fails, make sure that you have the required
   apt packages installed ([more details](https://www.psycopg.org/docs/install.html#build-prerequisites)).
3. Create a PostgreSQL user named `studio`:
    ```sudo -u postgres createuser -d -l -P studio```
4. Create a database named `studio`:
    ```sudo -u postgres createdb -O studio studio```
5. Add `studio.local` to `/etc/hosts` as an alias of 127.0.0.1:
   ```
   127.0.0.1    localhost studio.local  # studio.local can be added on the same line as localhost
    ...
   ```
5. Create a `settings.py` file (copy of `settings.example.py`). This file is gitignored,
and it must not be committed.
    - Change the `'PASSWORD'` variable in the `DATABASE` settings.
    - All the settings in settings.py that ultimately have to be changed are set to 'CHANGE-ME'.
    You can look for this phrase to make sure that everything that needs to be adjusted
    has been adjusted. However, for local development at this stage only the database
    password actually has to be set for the project to run.
    - Optionally: configure your IDE database connection.
6. Add a Google Storage Credentials file `blender-cloud-credentials.json` in the
`studio/` folder.
6. In the command line, activate the virtual environment created by poetry:
    ```poetry shell```
    - Configure your IDE to use the venv by default.
7. In the project folder, run migrations: `./manage.py migrate`
8. Create a superuser: `echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'password')" | python manage.py shell`
9. Run the server: `./manage.py runserver 8001`. The project will be available at
    `studio.local:8001`.
10. (Optional) Install pre-commit hooks (see [pre-commit details](docs/development.md#before-commiting)):
```pre-commit install```
11. In the admin panel (http://studio.local:8001/admin), edit the `Site` object's domain.
    The default domain is `example.com`; change it to `studio.local:8001`. This will make
    it possible to immediately view objects created/edited via admin on site.
12. Set up the [Blender ID server](#blender-id-authentication) for authentication
    and [MeiliSerach server](#search) for the search functionality.


## Data import
You can add objects to the database manually via the Django's Admin panel.
There are also commands that import data from the Cloud, but running them requires some additional
arrangements - ask Francesco about it.
Another way is to upload data fixtures created from the staging database.

### Fixtures
Your public key has to be added to the known hosts in the staging server.
1. Copy the fixtures directory from staging to your machine:
    ```
    scp -rp root@37.139.8.152:/var/www/blender-studio/fixtures/ .
    ```
2. Run:
    ```
    ./manage.py loaddata --exclude auth.permission ./fixtures/fixture_users.json
    ./manage.py loaddata ./fixtures/fixture_static_assets.json
    ./manage.py loaddata ./fixtures/fixture_comments.json
    ./manage.py loaddata ./fixtures/fixture_training.json
    ./manage.py loaddata ./fixtures/fixture_films.json
    ./manage.py loaddata ./fixtures/fixture_blog.json
    ```
   The order may be changed, but some of the fixtures have to be loaded before certain
   other ones that depend on them.

In case of some of the models, adding objects to the database will trigger post-save
signals which update the search index.

#### Troubleshooting
If the `loaddata` command hangs, disable the post-save signals: in the `search/app.py`
file comment out the `ready()` function definition (specifically, the import statement
in its body).

The staging database has different content type ids than the databases created recently
(after the 'static_assets' app was renamed). This may cause problems with loading
fixtures. The most probable case is that some users have permissions assigned, and these
permissions relate to nonexistent content types.

To fix this, open the `fixture_users.json` file, find the occurrences of the string
`"user_permissions": [` (including the inverted commas).
If any user has any numbers listed there, delete all those numbers, and leave an
empty array, like this: `user_permissions": []`.

You can then manually reassign user permissions in the admin panel.


## Blender ID authentication setup
Login to Blender Studio is possible using Blender ID. For development, you can set up a local
instance of [Blender ID](https://docs.blender.org/id/development_setup/). You'll need
**MySQL** (or MariaDB) and **npm** installed. It is also possible to use a
[Docker container](https://hub.docker.com/_/mariadb/) with the database, e.g. like this:
```
docker run --rm --name blender-id-db -e MYSQL_USER=blender_id -e \
MYSQL_PASSWORD=blender_id -e MYSQL_DATABASE=blender_id -e MYSQL_ALLOW_EMPTY_PASSWORD=yes \
-p 3306:3306 -it -v blender_id:/var/lib/mysql mariadb:latest
```

After configuring and running the Blender ID application, in its admin (http://id.local:8000/admin/)
create a new OAuth2 application:
 - Redirect url: `http://studio.local:8001/oauth/authorized`
 - Client type: Confidential
 - Authorization grant type: Authorization code

Copy the **Cliend id** and **Cliend secret** to the studio's `settings.py` as `"OAUTH_CLIENT"`
and `"OAUTH_SECRET"` in the `BLENDER_ID` settings.


## Search setup
For a complete description of the search feature, see the [search documentation](search.md).
It also includes [production setup](search.md#deployment-to-production) and
[troubleshooting](search.md#troubleshooting) instructions.

1. [Install](https://docs.meilisearch.com/guides/advanced_guides/installation.html) and launch
MeiliSearch:
    ```
    curl -L https://install.meilisearch.com | sh
    ./meilisearch
    ```
2. With the project's venv activated, create indexes and fill them with data:
    ```
    ./manage.py create_search_indexes
    ./manage.py index_documents
    ```

The server will be available on port `7700` by default.
If you change it, adjust the `MEILISEARCH_API_ADDRESS` in settings_common.py as necessary.


## Workflow

#### Before committing
The following assumes that the virtual environment is activated: `poetry shell`.

[Pre-commit hooks](https://pre-commit.com) are responsible for automatically running black, mypy,
etc. on the staged files, before each commit. If there are issues, committing is aborted.

The pre-commit configuration is in the [.pre-commit-config.yaml](../.pre-commit-config.yaml) file.

In case of emergency, it is possible to
[disable one or more hooks](https://pre-commit.com/#temporarily-disabling-hooks). To completely
disable all the hooks, run `pre-commit uninstall`. To enable them again, run `pre-commit install`.

You can also execute the `test.sh` script: it runs mypy, black, tests, eslint, and stylelint on the
entire project (so it's slower and more likely to error out).


#### Git workflow
1. Rebase, don't merge.
2. `develop` is the working branch. In order to work on a task, create a new branch off `develop`.
It is technically possible to `git push --force` to `develop`, however please consider at least warning
other developers if you plan to do it.
