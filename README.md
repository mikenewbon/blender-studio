# Blender Studio

## Requirements

- Python 3.8.x
- poetry
- PostgreSQL

All the Python-specific details are in the `pyproject.toml` file, but this is something
that poetry takes care of -- there's no need to install anything manually.


## Run locally

1. Clone the repo
2. Run `poetry install`
   - if the installation of psycopg2 fails, make sure that you have the required 
   apt packages installed (more details [here](https://www.psycopg.org/docs/install.html))

3. Create a database named `studio` in psql:
    ```CREATE DATABASE studio;```
4. Set password in psql console:
    ```ALTER USER postgres PASSWORD 'MyNewPassword';```
5. Create a `settings.py` file (copy of `settings.example.py`). This file is gitignored,
don't change it.
    - Change the `'PASSWORD'` variable in the `DATABASE` settings.
    - Add `'127.0.0.1'` to allowed hosts.
    - Optionally: configure your IDE database connection.
6. In the project folder, run migrations: `./manage.py migrate`
7. Create a superuser: `./manage.py createsuperuser`
8. Run the project: `./manage.py runserver`


## Before commiting

Run the `test.sh` script.
