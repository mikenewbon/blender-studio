# Generated by Django 3.0.8 on 2020-07-31 15:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(model_name='revision', old_name='subtitle', new_name='description',),
    ]
