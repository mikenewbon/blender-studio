# Generated by Django 3.0.9 on 2020-10-23 15:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0032_update_section'),
    ]

    operations = [
        migrations.AlterModelOptions(name='training', options={'ordering': ['-date_created']},),
    ]