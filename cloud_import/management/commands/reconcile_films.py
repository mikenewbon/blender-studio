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

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slug', dest='slugs', action='append', help="provides film slugs"
        )

        parser.add_argument(
            '--all', action='store_true', help='Reconcile all trainings',
        )

    def assign_user(self, asset, node_doc):

        user, _ = self.get_or_create_user(node_doc['user'])
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

    def reconcile_film_asset(self, asset_doc, collection: models_films.Collection):
        asset_slug = str(asset_doc['_id'])
        self.console_log(f"Processing asset with {asset_slug}")
        try:
            asset = models_films.Asset.objects.get(slug=asset_slug)
        except models_films.Asset.DoesNotExist:
            asset = models_films.Asset.objects.create(
                slug=asset_slug,
                film=collection.film,
                collection=collection,
                description=asset_doc['description'],
                category='artwork',
                is_published=True,
            )

        # Set Production File category if asset is of type file and file is an image
        if (
            'content_type' in asset_doc['properties']
            and asset_doc['properties']['content_type'] == 'file'
        ):
            asset.category = 'production_file'

        # Set Tags
        if 'tags' in asset_doc['properties']:
            asset.tags.add(*asset_doc['properties']['tags'])

        # Assign static asset
        file_doc = mongo.files_collection.find_one(
            {'_id': ObjectId(asset_doc['properties']['file'])}
        )
        if 'picture' in asset_doc:
            thumbnail_file_doc = mongo.files_collection.find_one(
                {'_id': ObjectId(asset_doc['picture'])}
            )
        else:
            thumbnail_file_doc = None
        asset.static_asset = self.get_or_create_static_asset(file_doc, thumbnail_file_doc)
        asset.save()

        self.reconcile_film_asset_comments(asset)

    def get_or_create_collection(self, collection_doc, film):
        collection_slug = str(collection_doc['_id'])

        try:
            self.console_log(f"Getting collection {collection_slug}")
            collection = models_films.Collection.objects.get(slug=collection_slug)
        except models_films.Collection.DoesNotExist:
            self.console_log(f"Not found, creating collection {collection_slug}")
            collection = models_films.Collection.objects.create(
                order=1, film=film, name=collection_doc['name'], slug=collection_slug,
            )
        if 'order' in collection_doc['properties']:
            collection.order = collection_doc['properties']['order']

        if 'description' in collection_doc:
            collection.text = collection_doc['description']

        collection.date_created = pytz.utc.localize(collection_doc['_created'])
        collection.date_updated = pytz.utc.localize(collection_doc['_updated'])
        collection.user, _ = self.get_or_create_user(collection_doc['user'])
        collection.save()

        # Ensure media
        if 'picture' in collection_doc and collection_doc['picture']:
            self.reconcile_file_field(collection_doc['picture'], collection, 'thumbnail')

        # Traverse parent
        if 'parent' in collection_doc and collection_doc['parent']:
            parent_collection_doc = mongo.nodes_collection.find_one(
                {'_id': ObjectId(collection_doc['parent'])}
            )
            if parent_collection_doc:
                collection.parent = self.get_or_create_collection(parent_collection_doc, film)
                collection.save()
            else:
                self.console_log(f"Parent collection {collection_doc['parent']} not found")

        return collection

    def fetch_film_project_docs(self):
        """Get all films from mongoDB."""
        for film_doc in mongo.projects_collection.find(
            {'is_private': False, 'status': 'published', 'category': {'$in': ['film']}}
        ):
            self.console_log(f"Processing {film_doc['name']}")
            yield film_doc

    def fetch_film_collection_docs(self, film_doc):
        groups = mongo.nodes_collection.find(
            {
                'project': film_doc['_id'],
                '_deleted': {'$ne': True},
                'node_type': 'group',
                'properties.status': 'published',
            }
        )
        for group in groups:
            self.console_log(f"Fetching collection doc {group['name']}")
            yield group

    def fetch_film_asset_docs(self, film_doc, group_doc=None):
        parent = None if not group_doc else group_doc['_id']
        assets = mongo.nodes_collection.find(
            {
                'project': film_doc['_id'],
                'parent': parent,
                '_deleted': {'$ne': True},
                'node_type': 'asset',
                'properties.status': 'published',
            }
        )
        for asset in assets:
            self.console_log(f"Fetching asset doc {asset['name']}")
            yield asset

    def reconcile_film(self, film_doc):
        film = models_films.Film.objects.get(slug=film_doc['url'])

        for group_doc in self.fetch_film_collection_docs(film_doc):
            collection = self.get_or_create_collection(group_doc, film)

            for asset_doc in self.fetch_film_asset_docs(film_doc, group_doc):
                self.reconcile_film_asset(asset_doc, collection)

        # Create chapter where we relocate top level content
        collection, _ = models_films.Collection.objects.get_or_create(
            order=0, film=film, name="Top", slug=f"top-{film.slug}"
        )
        for asset_doc in self.fetch_film_asset_docs(film_doc):
            self.reconcile_film_asset(asset_doc, collection)

    def handle(self, *args, **options):

        if options['all']:
            self.console_log("Reconciling all films")
            for training_doc in self.fetch_film_project_docs():
                self.reconcile_film(training_doc)
            return

        for film_slug in options['slugs']:
            film_doc = mongo.projects_collection.find_one(
                {'url': film_slug, '_deleted': {'$ne': True}}
            )
            self.reconcile_film(film_doc)
