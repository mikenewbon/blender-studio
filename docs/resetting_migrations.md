# Resetting migrations and introducing new User model

This how-to is based on [a comment to ticket #25313](https://code.djangoproject.com/ticket/25313#comment:18).
The reason migrations had been reset in this project are the following:

* Replacing `auth.User` model;
  which is not possible mid-project without migrations being reset;
* Simplifying test runs;
* Having a possibility of running tests with in-memory SQLite instead of PostgreSQL.

### Step zero: backup your production database

Make sure you make backups of your production database.

### Step one: an identical User model and initial migrations

#### users app

Because you probably have a multitude of FKs to the `auth.User` model, it's easier to create a completely
separate app that will contain it. This ensures

### Re-creating migrations

```
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
./manage.py makemigrations
```

#### Some data migrations have to be added manually

* `blender_id_oauth_client` constraint:

```
        # FIXME(anna): because this table is en external dependency,
        # there's no other way to enforce this contraint
        # Addin OAuthUserInfo._meta.get_field('oauth_user_id')._unique = True
        # would generate a migration inside `blender_id_oauth_client`
        migrations.RunSQL(
            # Generated with sqlmigrate from an automatic migration that was removed right after
            # e.g. if blender_id_oauth_client migration number is NNNN
            sql=[
                # ./manage.py sqlmigrate blender_id_oauth_client NNNN
                'ALTER TABLE "blender_id_oauth_client_oauthuserinfo" '
                'ADD CONSTRAINT "blender_id_oauth_client__oauth_user_id_b1e52371_uniq" '
                'UNIQUE ("oauth_user_id");',
                'CREATE INDEX "blender_id_oauth_client__oauth_user_id_b1e52371_like" '
                'ON "blender_id_oauth_client_oauthuserinfo" ("oauth_user_id" varchar_pattern_ops);',
            ],
            reverse_sql=[
                # ./manage.py sqlmigrate blender_id_oauth_client NNNN --backwards
                'DROP INDEX IF EXISTS "blender_id_oauth_client__oauth_user_id_b1e52371_like";',
                'ALTER TABLE "blender_id_oauth_client_oauthuserinfo" '
                'DROP CONSTRAINT IF EXISTS "blender_id_oauth_client__oauth_user_id_b1e52371_uniq";',
            ],
        )
```

* `can_view_content` to the `demo` and `subscriber` groups:

```
def add_can_view_content_permission_to_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Profile = apps.get_model('profiles', 'Profile')
    content_type = ContentType.objects.get_for_model(Profile)
    # permissions are created in a `post_migrate` signal and won't be available until the **next** ./manage.py migrate,
    # causing __fake__.DoesNotExist: Permission matching query does not exist
    permission, _ = Permission.objects.get_or_create(
        codename='can_view_content',
        content_type=content_type,
        name='Can view subscription-only content',
    )
    # Add this permission to the groups that are currently interpreted as having active subscription status
    for group_name in ('demo', 'subscriber'):
        # Create these groups, so that tests and newly setup dev environments worked as expected
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(permission)

    ...
    migrations.RunPython(add_can_view_content_permission_to_groups),
    ...
```
At this point testsuite should complete without issues and a commit can be made.

## Deployment steps

```
echo 'TRUNCATE TABLE django_migrations;' | psql --dbname=postgresql://studio:PASSWORD@localhost:5432/studio
git pull
./manage.py migrate --fake
```

### rewrite content types

Now rewrite LogEntry to keep the admin history intact:
```
./manage.py shell
>>>
>>> from django.contrib.admin.models import LogEntry
>>> from django.contrib.contenttypes.models import ContentType
>>>
>>> auth_user = ContentType.objects.get(app_label='auth', model='user')
>>> new_user = ContentType.objects.get(app_label='users', model='user')
>>>
>>> for le in LogEntry.objects.filter(content_type=auth_user):
...     le.content_type = new_user
...     le.save()
...
>>> from actstream.models import Action  # same for Action

>>> for le in Action.objects.filter(actor_content_type=auth_user):
>>>     le.actor_content_type = new_user
>>>     le.save()
```

Run this and **make sure to answer NO** to find more models that might need refer to `ContentType` that need updating:

```
./manage.py remove_stale_contenttypes
```
