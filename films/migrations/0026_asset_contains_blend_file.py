# Generated by Django 3.0.8 on 2020-07-23 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0025_create_film_flat_page'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='contains_blend_file',
            field=models.BooleanField(default=False, help_text='Is the asset a .blend file or a package containing .blend files?'),
        ),
    ]