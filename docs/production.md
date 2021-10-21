# Deployment to production

## Requirements

Production requirements include development requirements and add a few extra packages:

* [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)
* [nginx](https://nginx.org/en/)
* [systemd](https://systemd.io/) >= 211
* [Let's Encrypt certbot](https://certbot.eff.org/)

The following document assumes that the Studio is being deployed on Ubuntu.
If you are using a different distro, some paths, such as location of nginx configuration files might differ.

## Working directory

Source code of the Blender Studio is assumed to be located in `/var/www/blender-studio/`:
```
cd /var/www
git clone git@git.blender.org:blender-studio.git
git checkout production
```

### Setup virtualenv and install Python dependencies

Production virtualenv should be located in `/var/www/venv`, create it using the following commands:
```
cd /var/www
virtualenv -p /usr/bin/python3 venv
```

Then activate the virtualenv and install all the Python dependencies:
```
cd /var/www/blender-studio
source /var/www/venv/bin/activate
pip install poetry==1.1.6
poetry install
```

### Production `settings.py`

Copy `settings.example.py` into production `settings.py`:
```
cp studio/settings.example.py studio/settings.py
```
Make sure to change the following settings in the newly copied `settings.py`:

* `SECRET_KEY`: must be a random hard-to-guess string (keep it safe, never commit it into any repositories);
* `DEBUG`: must be `False`;
* `os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"` line must be commented out or deleted;
* `ALLOWED_HOSTS` must include whichever domain Studio is running on;
* `DATABASE` must be updated with database credentials from your production db;
* the rest of `CHANGE_ME` values that refer to various integrations, such as Blender ID, AWS S3, AWS CloudFront etc must be updated as well.

After `settings.py` have been updated, run the following commands to migrate your database and collect the static files:
```
cd /var/www/blender-studio
source /var/www/venv/bin/activate
./manage.py migrate
./manage.py collectstatic --no-input
```

## Configuration files

All the configuration files use domain `studio.blender.org`, make sure to change it when appropriate.

Some configuration files have `CHANGE_ME` values which must be replaced with production values, see sections below for more details.

The [deploy/](deploy/) directory contains configuration files used in production, with exact paths kept intact,
e.g. a file `deploy/var/www/config/nginx_studio.conf` must be copied to `/var/www/config/nginx_studio.conf`.

While logged in as `root`, copy the contents of `deploy` into their appropriate locations:

```
cp deploy/etc/systemd/system/* /etc/systemd/system/
cp deploy/var/www/config/* /var/www/config/
cp -r deploy/var/www/.config/* /var/www/.config/
```

All of the Blender Studio services, with an exception of nginx, run as `www-data` user and `www-data` group.
Make sure the following directories are owned by this user, otherwise services won't start or work properly later:

```
chown www-data:www-data /var/www
chown www-data:www-data -R /var/www/blender-studio
chown www-data:www-data -R /var/www/config
chown www-data:www-data -R /var/www/venv
chgrp www-data /var/www
chmod g+s /var/www
find /var/www -type d -exec chgrp www-data {} +
find /var/www -type d -exec chmod g+s {} +
```

In case you have to edit some of the files in production, be sure to edit them as `www-data` user, e.g.
```
sudo -Hu www-data vim training/management/commands/my_command.py
```

**⚠️ The steps below assume that all the configuration files have been copied to their appropriate locations.**

### Meilisearch

#### Install meilisearch

Install MeiliSearch following the instructions in **Step 1** [of the official documentation](https://docs.meilisearch.com/create/how_to/running_production.html#step-1-install-meilisearch).

The systemd service file is already included in Blender Studio's repository, previously copied to `/etc/systemd/system/meilisearch.service`.

Because our `meilisearch` service isn't run as `root`, it must be allowed to be executed by other users. Run the following command as `root`:
```
chmod o+x /usr/bin/meilisearch
```

**⚠️ `/etc/systemd/system/meilisearch.service` must be updated before `meilisearch` can run in production.**

#### Configure `meilisearch.service`

In production, the server should be run in the `Production` mode, and with a master key. Running the server without a master key is only possible in the development mode, as it makes all routes accessible and constitutes a security issue.
The details are explained in [the authentication guide](https://docs.meilisearch.com/guides/advanced_guides/authentication.html).

A random master key must be generated and placed in the `meilisearch.service`. Master key can be generated with the following command:
```
head /dev/urandom | tr -dc A-Za-z0-9 | head -c32
```
Use the resulting value to replace `CHANGE_ME` of the following line in `/etc/systemd/system/meilisearch.service`:
```
Environment=MEILI_MASTER_KEY=CHANGE_ME
```

**(Optional)** if you are using Sentry, replace `CHANGE_ME` part of `Environment=SENTRY_DSN` line with your [Sentry DSN](https://docs.sentry.io/product/sentry-basics/dsn-explainer/), and comment out `Environment=MEILI_NO_SENTRY=1` line.

Now, enable and start `meilisearch` with the following commands:
```
systemctl enable meilisearch
systemctl start meilisearch
```

#### Configure Studio integration with meilisearch

When the server is running with a master key, all the requests sent to it have to include the `X-Meili-API-Key` header with either the public key (for search requests), or the private key (for all other requests).
In practise, the front end needs the public key, and the back end (management commands, signals) - the private one.

When you change the master key, the public and private keys change too, and you will have to update them in `settings.py`.

Use the master key generated earlier to retrieve the public and the private key:
```
curl -H "X-Meili-API-Key: MASTER-KEY" -X GET 'http://localhost:7700/keys'
```
Update `/var/www/blender-studio/studio/settings.py` with these values:
```
MEILISEARCH_PUBLIC_KEY = 'PublicKeyGoesHere'
MEILISEARCH_PRIVATE_KEY = 'PrivateKeyGoesHere'
```

Since all the search requests have to be sent to `https://studio.blender.org/s/`,
update the `MEILISEARCH_API_ADDRESS` variable in `settings.py`:
```
MEILISEARCH_API_ADDRESS = 'https://studio.blender.org/s/'
```

To index available data, activate the virtualenv, and run `create_search_indexes` and `index_documents` commands,
see [search management commands](../docs/search.md#management-commands) for more details.

### uWSGI

Production Blender Studio is using uWSGI, its configuration is in `/etc/systemd/system/studio.service`.
Enable and start it with the following commands:
```
systemctl enable studio
systemctl start studio
```

### Nginx

Nginx config can be found in the `/var/www/config` directory. Symlink it into `sites-enabled` directory:
```
ln -s /var/www/config/nginx_studio.conf /etc/nginx/sites-enabled/nginx_studio.conf
```

#### Configure certbot

Follow [the official instructions](https://certbot.eff.org/lets-encrypt/ubuntufocal-nginx) to install certbot and get a Let's Encrypt certificate for your domain.

Nginx configuration file included into this repository assume that Studio is running on the `studio.blender.org` domain,
so you must review the `/var/www/config/nginx_studio.conf` configuration files to make sure the right domain is used instead.


#### Test and start nginx
Test the configuration:
```
nginx -t
```

If there are no errors, enable and start nginx:
```
systemctl enable nginx
systemctl start nginx
```

### Background tasks

Background tasks are used to handle things that aren't supposed to be happening during handling of HTTP requests,
such as sending emails, making requests to Blender ID and calling various APIs for video processing.

The systemd unit that manages this process is `/etc/systemd/system/studio-background.service`.
Background tasks can be enabled and started with the following commands:
```
systemctl enable studio-background
systemctl start studio-background
```

### Periodic tasks

Production Studio uses [systemd timers](https://www.freedesktop.org/software/systemd/man/systemd.timer.html) instead of `crontab` for its periodic tasks.
The following periodic services exist at the moment:

* [studio-clearsessions.timer](deploy/etc/systemd/system/studio-clearsessions.timer): calls [clearsessions](https://docs.djangoproject.com/en/3.0/ref/django-admin/#clearsessions);
* [studio-process-deletion-requests.timer](deploy/etc/systemd/system/studio-process-deletion-requests.timer): processes outstanding account deletion requests;
* [studio-background-restart.timer](deploy/etc/systemd/system/studio-background-restart.timer): takes care of a heisenbug that causes background process to hang on rare occasion;
* [studio-stats.timer](deploy/etc/systemd/system/studio-stats.timer): calculates and stores Studio statistics, such as current number of active subscribers;
* [studio-clock-tick.timer](deploy/etc/systemd/system/studio-clock-tick.timer): processes subscriptions payments and cancellations, see [Looper](https://developer.blender.org/source/looper/) for more details.

Each of the above timer files have a corresponding `.service` file located at the same directory, which is invoked when a timer is executed.

Each of the timers must be enabled and started individually with the following commands:
```
systemctl enable <NAME>.timer
systemctl start <NAME>.timer
```
For example, to enable `studio-clearsessions`:
```
systemctl enable studio-clearsessions.timer
systemctl start studio-clearsessions.timer
```

To view existing timers and details about when they were called last and other usefull info:
```
systemctl list-timers --all
```
