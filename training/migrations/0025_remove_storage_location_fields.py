# Generated by Django 3.0.10 on 2020-09-30 11:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0024_update_file_fields'),
    ]

    operations = [
        migrations.RemoveField(model_name='asset', name='storage_location',),
        migrations.RemoveField(model_name='training', name='storage_location',),
        migrations.RemoveField(model_name='video', name='storage_location',),
    ]