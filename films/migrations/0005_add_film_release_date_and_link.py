# Generated by Django 3.0.4 on 2020-06-04 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0004_auto_20200603_1552'),
    ]

    operations = [
        migrations.AddField(
            model_name='film',
            name='release_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='film',
            name='watch_link',
            field=models.URLField(blank=True, null=True),
        ),
    ]
