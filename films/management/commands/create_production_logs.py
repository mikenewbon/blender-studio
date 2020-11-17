# noqa: D100
from typing import Optional, Dict
import re

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
    """Create production logs."""

    help = 'Create production logs'

    def _get_or_create_production_log(self, collection):
        try:
            production_log = models_films.ProductionLog.objects.get(
                film=collection.film, name=collection.name
            )
        except models_films.ProductionLog.DoesNotExist:
            node_doc = mongo.nodes_collection.find_one({'_id': ObjectId(collection.slug)})
            user_doc = mongo.users_collection.find_one({'_id': node_doc['user']})
            user = _lookup_user(user_doc)
            print(user, node_doc)
            description = node_doc.get('description') or collection.text
            youtube_link = ''
            if description:
                youtube_iframe = re.findall(r'.iframe..*..iframe.', description)
                youtube_iframe = youtube_iframe[0] if youtube_iframe else None
                if youtube_iframe:
                    youtube_link = re.findall(r'src=.([^"\']+)', youtube_iframe)
                    youtube_link = youtube_link[0] if youtube_link else None
                    if 'embed/' in youtube_link:
                        # Replace with a normal watch link to stop youtube_modals.js from breaking
                        youtube_id = youtube_link.split('embed/')[-1]
                        youtube_link = f'https://www.youtube.com/watch?v={youtube_id}'
            if youtube_link:
                # Clean up the description
                description = description.replace(youtube_iframe, '')

            production_log = models_films.ProductionLog.objects.create(
                date_created=node_doc['_created'],
                date_updated=node_doc['_updated'],
                film=collection.film,
                name=collection.name,
                summary=description,
                start_date=collection.date_created,
                youtube_link=youtube_link,
                user=user,
            )
            thumbnail_doc = mongo.nodes_collection.find_one({'_id': ObjectId(collection.slug)})
            if thumbnail_doc and 'picture' in thumbnail_doc:
                self.reconcile_file_field(thumbnail_doc['picture'], production_log, 'thumbnail')
            if node_doc.get('picture'):
                self.reconcile_file_field(node_doc['picture'], production_log, 'thumbnail')
        return production_log

    def _get_or_create_production_log_entry(self, production_log, collection):
        try:
            production_log_entry = models_films.ProductionLogEntry.objects.get(
                legacy_id=collection.slug,
            )
        except models_films.ProductionLogEntry.DoesNotExist:
            node_doc = mongo.nodes_collection.find_one({'_id': ObjectId(collection.slug)})
            user_doc = mongo.users_collection.find_one({'_id': node_doc['user']})
            user = _lookup_user(user_doc)
            print(user, node_doc)

            production_log_entry = models_films.ProductionLogEntry.objects.create(
                date_created=node_doc['_created'],
                date_updated=node_doc['_updated'],
                production_log=production_log,
                description=node_doc.get('description') or collection.text,
                user=user,
                legacy_id=collection.slug,
            )
        return production_log_entry

    def _create_production_logs_for_film(self, slug):
        weeklies_collection = models_films.Collection.objects.get(slug=slug)
        for collection in weeklies_collection.child_collections.all():
            production_log = self._get_or_create_production_log(collection)
            for subcollection in collection.child_collections.all():
                production_log_entry = self._get_or_create_production_log_entry(
                    production_log, subcollection
                )
                for asset in subcollection.assets.all():
                    models_films.ProductionLogEntryAsset.objects.get_or_create(
                        asset=asset, production_log_entry=production_log_entry
                    )

    def handle(self, *args, **options):  # noqa: D102
        agent_327 = '570e7f14c379cf032c7b511f'
        caminandes_3 = '563cdc6bc379cf01030637ed'
        for slug in (caminandes_3, agent_327):
            self._create_production_logs_for_film(slug)
