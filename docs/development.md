# Development

## Requirements

- Python 3.8.x
- [poetry](https://python-poetry.org/)
- [PostgreSQL](https://www.postgresql.org/)

All the Python-specific details are in the `pyproject.toml` file, but this is something
that poetry takes care of -- there's no need to install anything manually.


## Set up instructions

1. Clone the repo.
2. Run `poetry install`
   - if the installation of psycopg2 fails, make sure that you have the required 
   apt packages installed (more details [here](https://www.psycopg.org/docs/install.html)).

3. Create a database named `studio` in psql console:
    ```CREATE DATABASE studio;```
4. Set user password in psql console:
    ```ALTER USER postgres PASSWORD 'MyNewPassword';```
5. Create a `settings.py` file (copy of `settings.example.py`). This file is gitignored,
and it must not be committed.
    - Change the `'PASSWORD'` variable in the `DATABASE` settings.
    - Add `'127.0.0.1'` to allowed hosts.
    - Optionally: configure your IDE database connection.
6. In the command line, activate the virtual environment created by poetry:
    ```source $(poetry env info --path)/bin/activate```
    - Configure your IDE to use the venv by default.
7. In the project folder, run migrations: `./manage.py migrate`
8. Create a superuser: `echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'password')" | python manage.py shell`
9. Run the server: `./manage.py runserver`
10. (Optional) Install pre-commit hooks (see [here](docs/development.md#before-commiting) for details):
```pre-commit install```


## Data import
Ask Francesco about it.


## Workflow

#### Before commiting

[Pre-commit hooks](https://pre-commit.com) are responsible for automatically running black, mypy,
etc. on the staged files, before each commit. If there are issues, committing is aborted.

The pre-commit configuration is in the [.pre-commit-config.yaml](../.pre-commit-config.yaml) file.

In case of emergency, it is possible to 
[disable one or more hooks](https://pre-commit.com/#temporarily-disabling-hooks). To completely 
disable all the hooks, run `pre-commit uninstall`.

You can also execute the `test.sh` script: it runs mypy, black, tests, eslint, and stylelint on the
entire project (so it's slower and more likely to error out).


#### Git workflow

1. Rebase, don't merge.
2. `develop` is the working branch. In order to work on a task, create a new branch off `develop`.
It is technically possible to `git push --force` to `develop`, however please consider at least warning
other developers if you plan to do it.
