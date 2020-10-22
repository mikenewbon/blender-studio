import datetime
import os
import pathlib
import shutil
import pytz
from bson import json_util, ObjectId
from typing import Optional
import botocore.exceptions as botocore_exceptions

from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings


from cloud_import.management import mongo
import comments.models as models_comments
import films.models as models_films
import static_assets.models as models_static_assets
from cloud_import.management.mixins import ImportCommand
from cloud_import.management import files
import training.models as models_training


class Command(ImportCommand):
    help = 'Reconcile attributes of static assets'

    def remove_webm_video_variations(self, static_asset: models_static_assets.StaticAsset):
        if static_asset.source_type != 'video':
            return

        for variation in static_asset.video.variations.filter(content_type='video/webm'):
            self.console_log(f"Removing {variation.source.name}")
            if variation.source.name:
                files.s3_client.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=variation.source.name
                )
            variation.delete()

    def get_film_asset_or_section(
        self, static_asset
    ) -> (Optional[models_training.Section], Optional[models_films.Asset]):
        try:
            section = static_asset.section
        except models_training.Section.DoesNotExist:
            section = None

        film_asset = static_asset.assets.first()

        # if not film_asset and not section:
        #     print(static_asset.original_filename)

        return section, film_asset

    def reconcile_free(self, static_asset: models_static_assets.StaticAsset):

        section, film_asset = self.get_film_asset_or_section(static_asset)

        node = mongo.nodes_collection.find_one(
            {'properties.file': ObjectId(static_asset.slug), 'permissions.world': {'$exists': True}}
        )
        if not node:
            return

        if film_asset:
            film_asset.is_free = True
            film_asset.save()

        if section:
            section.is_free = True
            section.save()

    def reconcile_content_disposition(self, static_asset: models_static_assets.StaticAsset):
        def update_object(key, disposition_metadata, content_type):
            self.console_log(f"Updating file {key}")
            self.console_log(f"\t Disposition: {disposition_metadata}")
            self.console_log(f"\t ContentType: {content_type}")
            try:
                files.s3_client.copy_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=static_asset.source.name,
                    CopySource={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key},
                    ContentDisposition=disposition_metadata,
                    ContentType=content_type,
                    MetadataDirective="REPLACE",
                )
            except botocore_exceptions.ClientError:
                self.console_log(f"File {key} is too large")
            except botocore_exceptions.ParamValidationError:
                self.console_log(f"ParamValidationError on {key}")
            except Exception as e:
                self.console_log(f"Generic exception on {key}")

        section, film_asset = self.get_film_asset_or_section(static_asset)

        filename = static_asset.original_filename
        if film_asset:
            filename = film_asset.name
        if section:
            filename = section.name

        if static_asset.source:
            extension = pathlib.Path(static_asset.source.name).suffix
            disposition = f'attachment; filename=\"{filename}{extension}\"'
            update_object(static_asset.source.name, disposition, static_asset.content_type)

        if static_asset.source_type == 'video':
            for variation in static_asset.video.variations.all():
                if not variation.source:
                    return
                extension = pathlib.Path(variation.source.name).suffix
                disposition = f'attachment; filename=\"{filename}{extension}\"'
                update_object(variation.source.name, disposition, variation.content_type)

    def handle(self, *args, **options):
        for static_asset in models_static_assets.StaticAsset.objects.all():
            # self.console_log(f"Fetching asset {static_asset.id} {static_asset.source}")
            file_doc = None
            filename = ''

            # First, attempt at looking up the file by uuid
            if static_asset.slug:
                file_doc = mongo.files_collection.find_one({'_id': ObjectId(static_asset.slug)})

            if not file_doc:
                # Build a file name to perform some searches
                filename = pathlib.Path(static_asset.source.name).stem
                filename = filename.split('-')[0]
                filename = f"{filename}*"

            # Perform various searches using the filename
            if not file_doc:
                file_doc = mongo.files_collection.find_one({'name': {'$regex': filename}})
            if not file_doc:
                file_doc = mongo.files_collection.find_one({'file_path': {'$regex': filename}})
            if not file_doc:
                file_doc = mongo.files_collection.find_one({'md5': {'$regex': filename}})
            if not file_doc:
                self.console_log(f"Missing {static_asset.id}")
                continue

            # self.get_or_create_static_asset(file_doc)
            # self.remove_webm_video_variations(static_asset)
            # self.reconcile_free(static_asset)
            self.reconcile_content_disposition(static_asset)
