## Preparing the database

1. download a backup dump of Blender Store's database;
2. install the required dependencies (they are defined as `dev` in Poetry config, so won't be automatically installed in production):
```
mysqlclient = "^2.0.3"
the-real-django-wordpress = {git = "https://github.com/anka-sirota/django-wordpress", rev = "dff975518720018103680f5557f4665a81076e2e"}
phpserialize = "^1.3"
```
3. run `./store_import/load_store_backup.sh -f path/to/wp_backup.sql.gz`
or
3. `echo 'CREATE DATABASE store' | mysql; gunzip -c /root/wp_store_backup-2021-06-11-1419.sql.gz | mysql store` if your are already running MariaDB.


It takes about 10 minutes for the database container to start and load the dump.

### Anonymising the data

This section is only relevant if you are testing locally.
Skip if the goal is to load Store data into a production database of `blender-studio`.

1. download anonimatron [https://github.com/realrolfje/anonimatron/releases/tag/v1.14](https://github.com/realrolfje/anonimatron/releases/tag/v1.14);
2. extract it into this directory (this will add a `anonimatron-1.14` directory here, in case you are downloading v1.14, for example);
3. go to Anonimatron's directory and modify `anonimatron.sh` changing the options to `-Xmx8G` to avoid `GC overhead limit exceeded` error;
4. run it:
```
path/to/anonimatron.sh/anonimatron.sh -config `realpath ./store_import/config.xml`
```

It takes about 20 minutes to complete its work.

## Importing Store data

To import data from a local Store database, use the following command:

```
DJANGO_SETTINGS_MODULE=studio.settings_store_import ./manage.py import_store_data
```

`import_store_data` adds apps that define read-only Wordpress models and other configuration that is not needed for the production settings, so there's a separate `settings_store_import.py` module for it.
