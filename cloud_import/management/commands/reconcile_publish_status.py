import bson
from bson import ObjectId

from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand
import training.models as models_training
import films.models as models_films


class Command(ImportCommand):
    help = 'Reconcile section and chapter publish status'

    def publish_item(self, item):
        try:
            chapter_doc = mongo.nodes_collection.find_one({'_id': ObjectId(item.slug)})
        except bson.errors.InvalidId:
            self.console_log(f"Skipping {item.slug}")
            return
        if not chapter_doc:
            self.console_log(f"Skipping {item.slug}")
            return

        if 'status' in chapter_doc['properties']:
            if chapter_doc['properties']['status'] == 'published':
                item.is_published = True
                item.save()

    def handle(self, *args, **options):

        for section in models_training.Section.objects.all():
            self.publish_item(section)

        for chapter in models_training.Chapter.objects.all():
            self.publish_item(chapter)

        for asset in models_films.Asset.objects.all():
            self.publish_item(asset)
