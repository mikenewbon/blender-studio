# Generated by Django 3.0.4 on 2020-06-03 08:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0002_auto_20200602_0745'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='storagebackend',
            name='film',
        ),
        migrations.RemoveField(
            model_name='storagebackend',
            name='training',
        ),
    ]