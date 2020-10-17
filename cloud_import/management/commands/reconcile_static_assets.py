import datetime
import os
import pathlib
import shutil
import pytz
from bson import json_util, ObjectId

from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from django.contrib.auth.models import User


from cloud_import.management import mongo
import comments.models as models_comments
import films.models as models_films
import static_assets.models as models_assets
from cloud_import.management.mixins import ImportCommand


class Command(ImportCommand):
    help = 'Reconcile duration and resolutions of static assets'

    def reconcile_file(self):
        pass

    def handle(self, *args, **options):
        for static_asset in models_assets.StaticAsset.objects.all():
            self.console_log(f"Fetching asset {static_asset.id}")
            file = mongo.files_collection.find_one(
                {'name': static_asset.original_filename, 'length': static_asset.size_bytes}
            )
