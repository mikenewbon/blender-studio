# Generated by Django 3.0.9 on 2021-01-06 09:39

from django.db import migrations
import django_jsonfield_backport.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_move_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='badges',
            field=django_jsonfield_backport.models.JSONField(blank=True, null=True),
        ),
    ]
