# Generated by Django 3.0.9 on 2020-08-25 10:57

import common.upload_paths
from django.db import migrations
import static_assets.models.static_assets


def set_default_picture_16_9(apps, schema_editor):
    Training = apps.get_model('training', 'Training')
    for training in Training.objects.filter(picture_16_9__isnull=True):
        training.picture_16_9 = training.picture_header
        training.save()


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0021_section_is_free'),
    ]

    operations = [
        migrations.RunPython(set_default_picture_16_9, reverse_code=migrations.RunPython.noop),
        migrations.RenameField(
            model_name='training', old_name='picture_16_9', new_name='thumbnail',
        ),
        migrations.AlterField(
            model_name='training',
            name='picture_header',
            field=static_assets.models.static_assets.DynamicStorageFileField(
                upload_to=common.upload_paths.get_upload_to_hashed_path
            ),
        ),
        migrations.AlterField(
            model_name='training',
            name='thumbnail',
            field=static_assets.models.static_assets.DynamicStorageFileField(
                upload_to=common.upload_paths.get_upload_to_hashed_path
            ),
        ),
    ]
