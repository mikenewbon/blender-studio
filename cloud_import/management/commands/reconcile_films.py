import datetime
import os
import pathlib
import shutil
import pytz
from bson import json_util, ObjectId

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand

from cloud_import.management import mongo
import comments.models as models_comments
import films.models as models_films
import static_assets.models as models_assets
from cloud_import.management.mixins import ImportCommand

User = get_user_model()


class Command(ImportCommand):
    help = 'Augment film assets with extra info'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slug', dest='slugs', action='append', help="provides film slugs"
        )

        parser.add_argument('--all', action='store_true', help='Reconcile all trainings')

    def assign_user(self, asset, node_doc):

        user, _ = self.get_or_create_user(node_doc['user'])
        self.console_log(f"Assign user {user.username} to asset {asset.id} - {asset.name}")

        asset.static_asset.user = user
        asset.static_asset.save()
        self.console_log(f"\tUpdated static_asset {asset.static_asset.id}")

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
