import datetime
import os
import pathlib
import shutil
import pytz
from bson import json_util, ObjectId

from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from django.contrib.auth import get_user_model

from cloud_import.management import mongo
import comments.models as models_comments
import films.models as models_films
import training.models as models_training
import static_assets.models as models_assets
from cloud_import.management.mixins import ImportCommand
import blog.models as models_blog

User = get_user_model()


class Command(ImportCommand):
    help = 'Reconcile attachments'

    def reconcile_node_attachments(self, node_doc, item, field_name):
        self.console_log(f"Reconciling attachments for node_doc {node_doc['_id']}")
        if 'properties' not in node_doc:
            return
        if 'attachments' not in node_doc['properties']:
            self.console_log("Node has no attachments")
            return
        for slug, attachment in node_doc['properties']['attachments'].items():
            # Replace the "{attachment <slug>" string with "{attachment <static_asset_id>"
            if 'oid' not in attachment:
                continue
            file_doc = mongo.files_collection.find_one({'_id': ObjectId(attachment['oid'])})
            if not file_doc:
                continue
            static_asset = self.get_or_create_static_asset(file_doc)
            item.attachments.add(static_asset)
            str_src = f"{{attachment {slug}"
            str_dst = f"{{attachment {static_asset.pk}"

            content = getattr(item, field_name)
            content = content.replace(str_src, str_dst)
            setattr(item, field_name, content)
            item.save()

    def handle(self, *args, **options):

        for section in models_training.Section.objects.all():
            if not section.slug:
                continue
            node_doc = mongo.nodes_collection.find_one({'_id': ObjectId(section.slug)})
            if not node_doc:
                continue
            self.reconcile_node_attachments(node_doc, section, 'text')

        for asset in models_films.Asset.objects.all():
            if not asset.slug:
                continue
            node_doc = mongo.nodes_collection.find_one({'_id': ObjectId(asset.slug)})
            if not node_doc:
                continue
            self.reconcile_node_attachments(node_doc, asset, 'description')
