import datetime
import os
import pathlib
import shutil
import pytz
from bson import json_util, ObjectId

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

    def reconcile_free(self, static_asset: models_static_assets.StaticAsset):

        try:
            section = static_asset.section
        except models_training.Section.DoesNotExist:
            section = None

        film_asset = static_asset.assets.first()

        # if not film_asset and not section:
        #     print(static_asset.original_filename)

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

    def handle(self, *args, **options):
        for static_asset in models_static_assets.StaticAsset.objects.filter(source_type='video'):
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
            # self.fix_empty_paths(static_asset)
            self.reconcile_free(static_asset)
