# Generated by Django 3.0.9 on 2020-12-09 14:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0057_unique_collection_slug'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productionlog',
            options={'ordering': ('-start_date', '-name'), 'verbose_name': 'production log', 'verbose_name_plural': 'production logs'},
        ),
    ]