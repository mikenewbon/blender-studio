# Blender Studio

## Overview

TODO: replace it with some real introduction

Blender Studio is the creative hub for your projects, powered by Free and Open Source Software.
Follow along with our expert team at your own pace - on every subject from Animation to UV unwrapping.
Classes, workshops and production lessons with .blend files included.
With 400+ hours of training and 1000's of production files, you're getting the best resources 
Blender has to offer.



### Local Development

#### Requirements

- Python 3.8.x
- [poetry](https://python-poetry.org/)
- [PostgreSQL](https://www.postgresql.org/)

All the Python-specific details are in the `pyproject.toml` file, but this is something
that poetry takes care of -- there's no need to install anything manually.


#### Set up

1. Clone the repo
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
7. Install pre-commit hooks (see below for details): ```pre-commit install```
8. In the project folder, run migrations: `./manage.py migrate`
9. Create a superuser: `echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'password')" | python manage.py shell`
10. Run the project: `./manage.py runserver`


#### Before commiting

[Pre-commit hooks](https://pre-commit.com) are responsible for automatically running black, mypy,
etc. on the staged files, before each commit. If there are issues, committing is aborted.

In case of emergency, it is possible to 
[disable one or more hooks](https://pre-commit.com/#temporarily-disabling-hooks). To completely 
disable all the hooks, run `pre-commit uninstall`.

You can also execute the `test.sh` script: it runs mypy, black, tests, eslint, and stylelint on the
entire project.


## License
