# Generated by Django 3.0.9 on 2020-08-24 15:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('static_assets', '0015_user_and_author_verbose_names'),
    ]

    operations = [
        migrations.RenameField(
            model_name='staticasset', old_name='source_preview', new_name='thumbnail',
        ),
    ]
