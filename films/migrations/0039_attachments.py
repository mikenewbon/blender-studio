# Generated by Django 3.0.9 on 2020-10-22 23:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('static_assets', '0027_sorting'),
        ('films', '0038_film_ordering'),
    ]

    operations = [
        migrations.AddField(
            model_name='filmflatpage',
            name='attachments',
            field=models.ManyToManyField(to='static_assets.StaticAsset'),
        ),
    ]