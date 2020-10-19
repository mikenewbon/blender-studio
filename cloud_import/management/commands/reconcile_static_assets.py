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


class Command(ImportCommand):
    help = 'Reconcile duration and resolutions of static assets'

    def handle(self, *args, **options):
        for static_asset in models_static_assets.StaticAsset.objects.all():
            self.console_log(f"Fetching asset {static_asset.id} {static_asset.source}")

            # Build a file name to perform some searches
            filename = pathlib.Path(static_asset.source.name).stem
            filename = filename.split('-')[0]
            filename = f"{filename}*"
            file = None

            # First, attempt at looking up the file by uuid
            if static_asset.slug:
                file = mongo.files_collection.find_one({'_id': ObjectId(static_asset.slug)})

            # Perform various searches using the filename
            if not file:
                file = mongo.files_collection.find_one({'name': {'$regex': filename}})
            if not file:
                file = mongo.files_collection.find_one({'file_path': {'$regex': filename}})
            if not file:
                file = mongo.files_collection.find_one({'md5': {'$regex': filename}})
            if not file:
                self.console_log(f"Missing {static_asset.id}")
                continue

            self.reconcile_static_asset(file, static_asset)
