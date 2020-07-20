# Development

## Requirements

- Python 3.8.x
- [poetry](https://python-poetry.org/)
- [PostgreSQL](https://www.postgresql.org/)

All the Python-specific details are in the `pyproject.toml` file, but this is something
that poetry takes care of -- there's no need to install anything manually.


## Set up instructions

1. Clone the repo.
2. Checkout the develop branch (master may be considerably outdated).
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
    You can look for this phrase to make sure that everything that needs to be adjusted, has been
    adjusted. However, for local development at this stage only the database password actually has
    to be set for the project to run.
    - Optionally: configure your IDE database connection.
6. In the command line, activate the virtual environment created by poetry:
    ```poetry shell```
    - Configure your IDE to use the venv by default.
7. In the project folder, run migrations: `./manage.py migrate`
8. Create a superuser: `echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'password')" | python manage.py shell`
9. Run the server: `./manage.py runserver`. The project will be available at `studio.local:8000`.
10. (Optional) Install pre-commit hooks (see [pre-commit details](docs/development.md#before-commiting)):
```pre-commit install```
11. In the admin panel (http://studio.local:8000/admin), edit the `Site` object's domain.
    The default domain is `example.com`; change it to `studio.local:8000`. This will make
    it possible to immediately view objects created/edited via admin on site.


## Data import
You can add objects to the database manually via the Django's Admin panel.
There are also commands that import data from the Cloud, but running them requires some additional
arrangements - ask Francesco about it.


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
