import datetime
import os
import pathlib
import mimetypes
from os.path import isfile, join
import hashlib

import shutil
import pytz
from bson import json_util, ObjectId
from typing import Optional
import botocore.exceptions as botocore_exceptions
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand

from cloud_import.management import mongo
import comments.models as models_comments
import films.models as models_films
import static_assets.models as models_static_assets
from cloud_import.management.mixins import ImportCommand
from cloud_import.management import files
import training.models as models_training

User = get_user_model()

USERNAME_TO_ID = {
    'fsiddi': 8,
    'andy': 9,
    'julien': 14,
    'demeter': 19,
    'vivien': 18,
    'hjalti': 11,
    'pablico': 12,
    'ricky': 30925,
    'angela': 2614,
}


class Command(ImportCommand):
    help = 'Import file for films'

    def add_arguments(self, parser):
        parser.add_argument('film_slug', type=str)
        parser.add_argument('weeklies_dir', type=str)

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

        filename = static_asset.original_filename

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

    def upload_file(self, file_name, bucket, object_name=None):
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param object_name: S3 object name. If not specified then file_name is used
        :return: True if file was uploaded, else False
        """

        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = file_name

        # Upload the file
        try:
            response = files.s3_client.upload_file(file_name, bucket, object_name)
        except botocore_exceptions.ClientError as e:
            print(e)
            return False
        return True

    def create_asset_from_file(
        self, weekly_name, user_name, file_path, collection: models_films.Collection
    ):
        file_path = pathlib.Path(file_path)
        self.console_log(f"Processing {file_path.name}")
        # Ensure it's an asset-worthy file
        # Upload to storage
        # Hash the filename
        # Create a 'path' with the author name and the date, which is unique enough
        unique_filename = f"{weekly_name}/{user_name}/{file_path.name}"

        hashed_name = hashlib.md5(unique_filename.encode("utf-8")).hexdigest()
        dest_file_path_s3 = pathlib.Path(hashed_name[:2], hashed_name, hashed_name).with_suffix(
            file_path.suffix
        )
        dest_file_path_s3 = str(dest_file_path_s3)
        content_disposition = f'attachment; filename=\"{file_path.name}\"'
        content_type, _ = mimetypes.guess_type(file_path.name)
        if files.file_on_s3(files.s3_client, settings.AWS_STORAGE_BUCKET_NAME, dest_file_path_s3):
            print(f"File {dest_file_path_s3} already exists on S3, skipping upload")
        else:
            with open(str(file_path), "rb") as f:
                files.s3_client.upload_fileobj(
                    f,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    dest_file_path_s3,
                    ExtraArgs={
                        'ContentDisposition': content_disposition,
                        'ContentType': content_type,
                    },
                )
        source_type = content_type.split('/')[0]
        if source_type not in {'image', 'video'}:
            source_type = 'file'

        # Create static_asset
        try:
            static_asset = models_static_assets.StaticAsset.objects.get(slug=hashed_name)
        except models_static_assets.StaticAsset.DoesNotExist:
            static_asset = models_static_assets.StaticAsset.objects.create(
                source=dest_file_path_s3,
                source_type=source_type,
                original_filename=file_path.name,
                size_bytes=file_path.stat().st_size,
                user_id=1,
                license_id=1,
                slug=hashed_name,
                content_type=content_type,
            )
        self.console_log(f"Processing file {static_asset.id}")
        # Reconcile creation date
        timestamp = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
        static_asset.date_created = pytz.utc.localize(timestamp)
        # Reconcile user
        username = user_name
        if username not in USERNAME_TO_ID:
            self.console_log(f"Username {username} not in USERNAME_TO_ID")
            username = 'fsiddi'
        user = User.objects.get(pk=USERNAME_TO_ID[username])
        static_asset.user = user
        static_asset.save()
        # Create film asset
        try:
            film_asset = models_films.Asset.objects.get(static_asset=static_asset)
        except models_films.Asset.DoesNotExist:
            film_asset = models_films.Asset.objects.create(
                film=collection.film,
                static_asset=static_asset,
                name=file_path.name,
                category='artwork',
                is_published=True,
            )
        # Reconcile the collection in case the file was moved
        film_asset.date_created = static_asset.date_created
        film_asset.collection = collection
        film_asset.save()
        self.console_log(f"Processed {film_asset}")

    def handle_user_weekly(self, user_dir: pathlib.Path, film):
        # Scan user dir
        def user_weekly_traverse(weekly_name, user_name, dir: pathlib.Path, collection=None):
            for entry in dir.iterdir():
                if entry.is_file():
                    if entry.name.startswith('.'):
                        continue
                    # Get the top collection
                    parent_collection = collection
                    if not parent_collection:
                        try:
                            parent_collection = models_films.Collection.objects.get(
                                film=film, slug=f"{film.slug}-top"
                            )
                        except models_films.Collection.DoesNotExist:
                            parent_collection = models_films.Collection.objects.create(
                                film=film, slug=f"{film.slug}-top", name='Top'
                            )
                    print(f"Processing file {entry.name}")
                    self.create_asset_from_file(weekly_name, user_name, entry, parent_collection)
                # If directories are found, tread them as collections
                elif entry.is_dir():
                    print(f"Collection {entry.name}")
                    try:
                        sub_collection = models_films.Collection.objects.get(
                            film=film, slug=entry.name
                        )
                    except models_films.Collection.DoesNotExist:
                        sub_collection = models_films.Collection.objects.create(
                            film=film,
                            slug=entry.name,
                            parent=collection,
                            name=entry.name.capitalize(),
                        )
                    user_weekly_traverse(weekly_name, user_name, entry, sub_collection)

        user_weekly_traverse(user_dir.parent.name, user_dir.name, user_dir)

    def handle(self, *args, **options):
        film_slug = options['film_slug']
        film = models_films.Film.objects.get(slug=film_slug)

        weeklies_dir = pathlib.Path(options['weeklies_dir'])
        # Traverse weeks
        # for weekly_dir in os.listdir(weeklies_dir):

        for weekly_dir in weeklies_dir.iterdir():
            if weekly_dir.is_file():
                continue
            # Handle content of weekly folder
            for user_dir in weekly_dir.iterdir():
                if user_dir.is_file():
                    continue
                self.handle_user_weekly(user_dir, film)
