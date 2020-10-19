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
    help = 'Augment film assets with extra info'

    # Set on handle and used in various functions to determine whether to
    # alter the database.
    dry_run = False

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slug', dest='film_names', action='append', help="provides film slugs"
        )
        parser.add_argument(
            '-d',
            '--dry-run',
            dest='dry_run',
            action='append',
            help="Do not alter database",
            nargs='?',
        )

    def assign_user(self, asset, node_doc):

        user = self.get_or_create_user(node_doc['user'])
        self.console_log(f"Assign user {user.username} to asset {asset.id} - {asset.name}")

        asset.static_asset.user = user
        asset.static_asset.save()
        self.console_log(f"\tUpdated static_asset {asset.static_asset.id}")

    def reconcile_film_asset_comments(self, asset: models_films.Asset):
        # Fetch comments
        comments = mongo.nodes_collection.find(
            {
                'node_type': 'comment',
                'parent': ObjectId(asset.slug),
                'properties.status': 'published',
                '_deleted': {'$ne': True},
            }
        )
        comments_count = 0
        for comment_doc in comments:
            self.console_log(f"Processing comment {comment_doc['_id']} for asset {asset.id}")
            comment = self.get_or_create_comment(comment_doc)
            models_films.AssetComment.objects.get_or_create(asset=asset, comment=comment)
            self.reconcile_comment_ratings(comment_doc)
            response_comments = mongo.nodes_collection.find(
                {
                    'node_type': 'comment',
                    'parent': comment_doc['_id'],
                    'properties.status': 'published',
                    '_deleted': {'$ne': True},
                }
            )
            comments_count += 1

            for reply_comment_doc in response_comments:
                reply_comment = self.get_or_create_comment(reply_comment_doc, comment_doc)
                models_films.AssetComment.objects.get_or_create(asset=asset, comment=reply_comment)
                self.reconcile_comment_ratings(reply_comment_doc)

        if comments_count > 0:
            self.console_log(f"Processed {comments_count} comments")

    def reconcile_film_assets(self, film: models_films.Film):
        for asset in models_films.Asset.objects.filter(film=film.pk):
            # Fetch original user from MongoDB
            self.console_log(f"Processing asset {asset.id} with slug {asset.slug}")
            node_doc = mongo.nodes_collection.find_one({'_id': ObjectId(asset.slug)})
            # Assign the user
            self.assign_user(asset, node_doc)
            # Reconcile comments
            self.reconcile_film_asset_comments(asset)

    def handle(self, *args, **options):

        if options['dry_run']:
            self.dry_run = True

        for film in models_films.Film.objects.all():
            self.reconcile_film_assets(film)
