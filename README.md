# Blender Studio

## Overview

TODO: replace it with some real introduction

Blender Studio is the creative hub for your projects, powered by Free and Open Source Software.
Follow along with our expert team at your own pace - on every subject from Animation to UV unwrapping.
Classes, workshops and production lessons with .blend files included.
With 400+ hours of training and 1000's of production files, you're getting the best resources 
Blender has to offer.



## Development

For the full developer documentation, see the [docs folder](docs).

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
7. In the project folder, run migrations: `./manage.py migrate`
8. Create a superuser: `echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'password')" | python manage.py shell`
9. Run the project: `./manage.py runserver`
10. (Optional) Install pre-commit hooks (see [here](docs/development.md#before-commiting) for details):
```pre-commit install```

See also how to [populate the database with data](docs/development.md#data-import).


### Credits


### License
