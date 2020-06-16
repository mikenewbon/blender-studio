# Generated by Django 3.0.4 on 2020-06-14 15:35

import assets.models.assets
import common.upload_paths
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0005_storage_backends'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staticasset',
            name='source_preview',
            field=assets.models.assets.DynamicStorageFileField(blank=True, upload_to=common.upload_paths.get_upload_to_hashed_path),
        ),
    ]