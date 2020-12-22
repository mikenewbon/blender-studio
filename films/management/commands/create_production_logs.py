# noqa: D100
import re

from bson import ObjectId

import films.models as models_films
from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand

# from static_assets.models.static_assets import StaticAsset
from users.blender_id import BIDSession


bid = BIDSession()


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
            user, _ = self.get_or_create_user(node_doc['user'])
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
                film=collection.film,
                name=collection.name,
                summary=description,
                start_date=collection.date_created,
                youtube_link=youtube_link,
                user=user,
            )
            production_log.date_created = self._localize_date(node_doc['_created'])
            production_log.date_updated = self._localize_date(node_doc['_updated'])
            production_log.save(update_fields=['date_created', 'date_updated'])

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
            nested_docs = self._get_nested_docs(collection.slug)
            if not nested_docs:
                self.console_log(f'{collection} is empty, not creating a production log entry')
                return
            for child in nested_docs:
                self._check_asset(production_log, child['_id'])
            user, _ = self.get_or_create_user(node_doc['user'])

            production_log_entry = models_films.ProductionLogEntry.objects.create(
                production_log=production_log,
                description=node_doc.get('description') or collection.text,
                user=user,
                legacy_id=collection.slug,
            )
            production_log_entry.date_created = self._localize_date(node_doc['_created'])
            production_log_entry.date_updated = self._localize_date(node_doc['_updated'])
            production_log_entry.save(update_fields=['date_created', 'date_updated'])
        return production_log_entry

    def _get_group(self, node_id):
        if not isinstance(node_id, ObjectId):
            node_id = ObjectId(node_id)
        return mongo.nodes_collection.find_one({'_id': node_id, 'node_type': 'group'})

    def _get_nested_docs(self, node_id):
        if not isinstance(node_id, ObjectId):
            node_id = ObjectId(node_id)
        return [
            _ for _ in mongo.nodes_collection.find({'parent': node_id}) if not _.get('_deleted')
        ]

    def _get_child_groups(self, node_id):
        nested_docs = self._get_nested_docs(node_id)
        nested_groups = []
        for _ in [_ for _ in nested_docs if _['node_type'] == 'group']:
            nested_group = mongo.nodes_collection.find_one({'_id': ObjectId(_['_id'])})
            if nested_group and not nested_group.get('_deleted'):
                nested_groups.append(nested_group)
        return nested_groups

    def _get_nested_assets(self, node_id):
        nested_docs = self._get_nested_docs(node_id)
        return [_ for _ in nested_docs if _['node_type'] == 'asset']

    def _get_film(self, node_doc):
        film_doc = mongo.projects_collection.find_one({'_id': ObjectId(node_doc['project'])})
        try:
            return models_films.Film.objects.get(title=film_doc['name'])
        except models_films.Film.DoesNotExist:
            self.console_log(f'No film found for {film_doc["name"]}')

    def _check_asset(self, production_log, asset_slug):
        asset_doc = mongo.nodes_collection.find_one({'_id': ObjectId(asset_slug)})
        asset_collection = models_films.Collection.objects.get(slug=asset_doc['parent'])
        if asset_doc['node_type'] == 'asset':
            self.assets_count += 1
            existing_film_asset = models_films.Asset.objects.filter(slug=asset_slug).first()
            collection_count = asset_collection.assets.count()
            print(f'Checking asset: {asset_slug} from {asset_collection} ({collection_count})')
            if existing_film_asset and existing_film_asset.static_asset:
                return
            self.missing_assets_count += 1
            self.reconcile_film_asset(asset_doc, asset_collection)
        elif asset_doc['node_type'] == 'group':
            print(f'Reconciling deeply nested collection: {asset_slug} from {asset_collection}')
            collection = self._create_collection_if_not_empty(asset_doc, production_log.film)
            if collection:
                self._fill_production_log_entry(production_log, collection)
        else:
            self.console_log(f'Unexpected node type in {asset_doc}')

    def _fill_production_log_entry(self, production_log, collection):
        production_log_entry = self._get_or_create_production_log_entry(production_log, collection)
        if not production_log_entry:
            return
        for asset in collection.assets.all():
            models_films.ProductionLogEntryAsset.objects.get_or_create(
                asset=asset, production_log_entry=production_log_entry
            )

    def _create_collection_if_not_empty(self, node_doc, film: models_films.Film):
        nested_docs = self._get_nested_docs(node_doc['_id'])
        if not nested_docs:
            self.console_log(f'{node_doc["_id"]} is an empty collection, skipping')
            return
        return self.get_or_create_collection(node_doc, film)

    def _check_collection(self, collection: models_films.Collection, film: models_films.Film):
        nested_groups = self._get_child_groups(collection.slug)
        nested_assets = self._get_nested_assets(collection.slug)
        asset_count = collection.assets.count()
        asset_count_orig = len(nested_assets)
        subcollection_count = collection.child_collections.count()
        subcollection_count_orig = len(nested_groups)
        group_doc = self._get_group(collection.slug)
        slug = str(group_doc['_id'])
        print(
            f'Collection: {collection}, {collection.slug}, ',
            f'Subcollections: {subcollection_count_orig} -> {subcollection_count}',
            f'Assets: {asset_count_orig} -> {asset_count}',
        )
        assert collection.slug == slug, f'{collection.slug} != {slug}'

        has_all_subcollections = subcollection_count == subcollection_count_orig
        # has_all_assets = asset_count == asset_count_orig

        if not has_all_subcollections:
            for collection_doc in nested_groups:
                self._create_collection_if_not_empty(collection_doc, film)
        # assert has_all_subcollections, f'{subcollection_count} != {subcollection_count_orig}'
        # assert has_all_assets, f'{asset_count} != {asset_count_orig}'

    def _create_production_logs_for_film(self, weekly_doc, film):
        slug = weekly_doc['_id']
        try:
            weeklies_collection = models_films.Collection.objects.get(slug=slug)
            self.console_log(f'Found collection for {slug}: {weeklies_collection}')
        except models_films.Collection.DoesNotExist:
            self.console_log(f'No collection for {slug}, creating')
            weeklies_collection = self.get_or_create_collection(weekly_doc, film)

        self._check_collection(weeklies_collection, film)
        for collection in weeklies_collection.child_collections.all():
            self._check_collection(collection, film)

            production_log = self._get_or_create_production_log(collection)
            for subcollection in collection.child_collections.all():
                self._check_collection(subcollection, film)
                # Sometimes assets are nested
                self._fill_production_log_entry(production_log, subcollection)
            # Sometimes assets are 'flat' in the collections
            if collection.assets.count():
                self._fill_production_log_entry(production_log, collection)

    def handle(self, *args, **options):  # noqa: D102
        self.missing_assets_count = self.assets_count = 0
        # agent_327 = '570e7f14c379cf032c7b511f'
        # caminandes_3 = '563cdc6bc379cf01030637ed'
        weeklies = list(mongo.nodes_collection.find({'name': 'Weeklies', 'node_type': 'group'}))
        self.console_log(f'Found {len(weeklies)}')
        # for slug in (caminandes_3, agent_327):
        for weekly_doc in weeklies:
            # if weekly_doc['_id'] != ObjectId(caminandes_3):
            #    continue
            film = self._get_film(weekly_doc)
            if not film:
                continue
            self.console_log(f'Processing {weekly_doc["name"]} for {film}')
            self._create_production_logs_for_film(weekly_doc, film)
        self.console_log(f'Total assets: {self.assets_count}, missing: {self.missing_assets_count}')
