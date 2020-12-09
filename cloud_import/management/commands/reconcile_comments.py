import datetime
import os
import pathlib
import tempfile
import shutil
import pytz
from bson import json_util, ObjectId

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand

from cloud_import.management import mongo

import films.models as models_films
import static_assets.models as models_assets
from cloud_import.management.mixins import ImportCommand
import training.models as models_training

User = get_user_model()


class Command(ImportCommand):
    help = 'Reconcile section and asset comments'

    def reconcile_item_comments(self, item):
        """Item can be either Section or Asset"""

        def process_comment(comment_doc, parent_doc=None):
            self.console_log(f"Processing comment {comment_doc['_id']} for item {item.id}")
            comment = self.get_or_create_comment(comment_doc, parent_comment_doc=parent_doc)
            if isinstance(item, models_training.Section):
                models_training.SectionComment.objects.get_or_create(section=item, comment=comment)
            elif isinstance(item, models_films.Asset):
                models_films.AssetComment.objects.get_or_create(asset=item, comment=comment)
            else:
                raise ValueError
            self.reconcile_comment_ratings(comment_doc)

            # Check for responses
            response_comments = mongo.nodes_collection.find(
                {
                    'node_type': 'comment',
                    '_deleted': {'$ne': True},
                    'parent': comment_doc['_id'],
                    'properties.status': 'published',
                }
            )

            for reply_comment_doc in response_comments:
                process_comment(reply_comment_doc, comment_doc)

        # Fetch comments
        comments = mongo.nodes_collection.find(
            {
                'node_type': 'comment',
                '_deleted': {'$ne': True},
                'parent': ObjectId(item.slug),
                'properties.status': 'published',
            }
        )
        comments_count = 0
        for comment_doc in comments:
            process_comment(comment_doc, parent_doc=None)
            comments_count += 1

        if comments_count > 0:
            self.console_log(f"Processed {comments_count} comments")

    def handle(self, *args, **options):

        for training in models_training.Training.objects.all():
            for chapter in training.chapters.all():
                for section in chapter.sections.all():
                    self.reconcile_item_comments(section)

        for film in models_films.Film.objects.filter():
            for collection in film.collections.all():
                for asset in collection.assets.all():
                    self.reconcile_item_comments(asset)
