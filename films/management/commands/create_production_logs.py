from typing import Optional, Dict
import datetime

from django.core.management.base import BaseCommand
import training.models as models_training
import static_assets.models as models_static_assets
from django.contrib.auth.models import User
from bson import ObjectId
import films.models as models_films
from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand
from profiles.blender_id import BIDSession


bid = BIDSession()


def _lookup_user(user_doc: Dict) -> Optional[User]:
    auth = next((_ for _ in user_doc.get('auth') if _.get('provider') == 'blender-id'), None)
    if not auth or not auth.get('user_id'):
        return None
    oauth_user_id = auth.get('user_id')
    oauth_user_info = bid.get_oauth_user_info(oauth_user_id=oauth_user_id)
    return oauth_user_info.user


class Command(ImportCommand):
    help = 'Create production logs'

    def get_or_create_production_log(self, collection):
        try:
            production_log = models_films.ProductionLog.objects.get(
                film=collection.film, name=collection.name
            )
        except models_films.ProductionLog.DoesNotExist:
            node_doc = mongo.nodes_collection.find_one({'_id': ObjectId(collection.slug)})
            user_doc = mongo.users_collection.find_one({'_id': node_doc['user']})
            user = _lookup_user(user_doc)
            production_log = models_films.ProductionLog.objects.create(
                date_created=node_doc['_created'],
                date_updated=node_doc['_updated'],
                film=collection.film,
                name=collection.name,
                summary=node_doc.get('description') or collection.text,
                start_date=collection.date_created,
                user=user,
            )
            # ?
            thumbnail_doc = mongo.nodes_collection.find_one({'_id': ObjectId(collection.slug)})
            if thumbnail_doc and 'picture' in thumbnail_doc:
                self.reconcile_file_field(thumbnail_doc['picture'], production_log, 'thumbnail')
            if node_doc.get('picture'):
                self.reconcile_file_field(node_doc['picture'], production_log, 'thumbnail')
        return production_log

    def get_or_create_production_log_entry(self, production_log, collection):
        try:
            production_log_entry = models_films.ProductionLogEntry.objects.get(
                legacy_id=collection.slug,
            )
        except models_films.ProductionLogEntry.DoesNotExist:
            node_doc = mongo.nodes_collection.find_one({'_id': ObjectId(collection.slug)})
            user_doc = mongo.users_collection.find_one({'_id': node_doc['user']})
            user = _lookup_user(user_doc)

            production_log_entry = models_films.ProductionLogEntry.objects.create(
                date_created=node_doc['_created'],
                date_updated=node_doc['_updated'],
                production_log=production_log,
                description=node_doc.get('description') or collection.text,
                user=user,
                legacy_id=collection.slug,
            )
        return production_log_entry

    def handle(self, *args, **options):
        agent_327 = '570e7f14c379cf032c7b511f'
        caminandes_3 = '563cdc6bc379cf01030637ed'
        weeklies_collection = models_films.Collection.objects.get(slug=agent_327)
        for collection in weeklies_collection.child_collections.all():
            production_log = self.get_or_create_production_log(collection)
            for subcollection in collection.child_collections.all():
                production_log_entry = self.get_or_create_production_log_entry(
                    production_log, subcollection
                )
                for asset in subcollection.assets.all():
                    models_films.ProductionLogEntryAsset.objects.get_or_create(
                        asset=asset, production_log_entry=production_log_entry
                    )
