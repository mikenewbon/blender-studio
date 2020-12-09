import datetime
import os
import pathlib
import tempfile
import shutil
import pytz
from bson import json_util, ObjectId

from django.core.management.base import BaseCommand
from django.core.files import File
from django.contrib.auth import get_user_model

from cloud_import.management import mongo

import films.models as models_films
import static_assets.models as models_assets
from cloud_import.management.mixins import ImportCommand
import training.models as models_training

User = get_user_model()


class Command(ImportCommand):
    help = 'Reconcile training data'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slug', dest='slugs', action='append', help="provides training slugs"
        )
        parser.add_argument('--all', action='store_true', help='Reconcile all trainings')

    def reconcile_training_section_comments(self, section: models_training.Section):
        # Fetch comments
        comments = mongo.nodes_collection.find(
            {
                'node_type': 'comment',
                '_deleted': {'$ne': True},
                'parent': ObjectId(section.slug),
                'properties.status': 'published',
            }
        )
        comments_count = 0
        for comment_doc in comments:
            self.console_log(f"Processing comment {comment_doc['_id']} for asset {section.id}")
            comment = self.get_or_create_comment(comment_doc)
            models_training.SectionComment.objects.get_or_create(section=section, comment=comment)
            self.reconcile_comment_ratings(comment_doc)
            response_comments = mongo.nodes_collection.find(
                {
                    'node_type': 'comment',
                    '_deleted': {'$ne': True},
                    'parent': comment_doc['_id'],
                    'properties.status': 'published',
                }
            )
            comments_count += 1

            for reply_comment_doc in response_comments:
                reply_comment = self.get_or_create_comment(reply_comment_doc, comment_doc)
                models_training.SectionComment.objects.get_or_create(
                    section=section, comment=reply_comment
                )
                self.reconcile_comment_ratings(reply_comment_doc)

        if comments_count > 0:
            self.console_log(f"Processed {comments_count} comments")

    def fetch_top_level_assets(self, training_doc):
        assets_top = mongo.nodes_collection.find(
            {
                'project': training_doc['_id'],
                'parent': {'$exists': False},
                '_deleted': {'$ne': True},
                'node_type': 'asset',
            }
        )
        for asset in assets_top:
            self.console_log(f"Fetched top level asset {asset['name']}")
            yield asset

    def get_or_create_section(self, section_doc, chapter):
        section_slug = str(section_doc['_id'])

        try:
            self.console_log(f"Getting section {section_doc['name']}")
            section = models_training.Section.objects.get(slug=section_slug)
        except models_training.Section.DoesNotExist:
            self.console_log(f"Not found, creating section {section_doc['name']}")
            section = models_training.Section.objects.create(
                index=1,
                chapter=chapter,
                name=section_doc['name'],
                slug=section_slug,
                text=section_doc['description'],
            )

        if 'order' in section_doc['properties']:
            section.index = section_doc['properties']['order']
        section.chapter = chapter
        section.date_created = pytz.utc.localize(section_doc['_created'])
        section.date_updated = pytz.utc.localize(section_doc['_updated'])
        section.user, _ = self.get_or_create_user(section_doc['user'])
        section.save()

        file_doc = mongo.files_collection.find_one(
            {'_id': ObjectId(section_doc['properties']['file'])}
        )

        if 'picture' in section_doc:
            thumbnail_file_doc = mongo.files_collection.find_one(
                {'_id': ObjectId(section_doc['picture'])}
            )
        else:
            thumbnail_file_doc = None
        section.static_asset = self.get_or_create_static_asset(file_doc, thumbnail_file_doc)
        section.save()

        # Reconcile comments
        self.reconcile_training_section_comments(section)

        return section

    def get_or_create_chapter(self, chapter_doc, training):
        chapter_slug = str(chapter_doc['_id'])

        try:
            self.console_log(f"Getting chapter {chapter_slug}")
            chapter = models_training.Chapter.objects.get(slug=chapter_slug)
        except models_training.Chapter.DoesNotExist:
            self.console_log(f"Not found, creating chapter {chapter_slug}")
            chapter = models_training.Chapter.objects.create(
                index=1, training=training, name=chapter_doc['name'], slug=chapter_slug
            )
        if 'order' in chapter_doc['properties']:
            chapter.index = chapter_doc['properties']['order']

        if 'description' in chapter_doc:
            chapter.description = chapter_doc['description']

        chapter.date_created = pytz.utc.localize(chapter_doc['_created'])
        chapter.date_updated = pytz.utc.localize(chapter_doc['_updated'])
        chapter.user, _ = self.get_or_create_user(chapter_doc['user'])
        chapter.save()

        # Ensure media
        if 'picture' in chapter_doc and chapter_doc['picture']:
            self.reconcile_file_field(chapter_doc['picture'], chapter, 'thumbnail')

        return chapter

    def get_or_create_training(self, training_doc):
        try:
            training = models_training.Training.objects.get(slug=training_doc['url'])
        except models_training.Training.DoesNotExist:
            self.console_log(f"Training {training_doc['url']} does not exist")
            training = models_training.Training.objects.create(
                name=training_doc['name'],
                slug=training_doc['url'],
                description=training_doc['summary'],
                summary=training_doc['description'],
                status=training_doc['status'],
                type=training_doc['category'],
            )
        training.date_created = pytz.utc.localize(training_doc['_created'])
        training.date_updated = pytz.utc.localize(training_doc['_updated'])
        training.save()

        # Ensure media
        if 'picture_header' in training_doc:
            self.reconcile_file_field(training_doc['picture_header'], training, 'picture_header')
        if 'picture_16_9' in training_doc:
            self.reconcile_file_field(training_doc['picture_16_9'], training, 'thumbnail')

        return training

    def fetch_training_docs(self):
        """Get all trainings from mongoDB."""
        for training_doc in mongo.projects_collection.find(
            {
                'is_private': False,
                'status': 'published',
                'category': {'$in': ['course', 'workshop']},
            }
        ):
            self.console_log(f"Processing {training_doc['category']} {training_doc['name']}")
            yield training_doc

    def fetch_training_chapter_docs(self, training_doc):
        groups = mongo.nodes_collection.find(
            {
                'project': training_doc['_id'],
                '_deleted': {'$ne': True},
                'node_type': 'group',
                'properties.status': 'published',
            }
        )
        for group in groups:
            self.console_log(f"Fetching chapter doc {group['name']}")
            yield group

    def fetch_training_section_docs(self, chapter: models_training.Chapter):
        """Yield assets inside of a group."""
        asset_docs = mongo.nodes_collection.find(
            {'parent': ObjectId(chapter.slug), '_deleted': {'$ne': True}, 'node_type': 'asset'}
        )
        for asset_doc in asset_docs:
            yield asset_doc

    def reconcile_training(self, training_doc):
        training = self.get_or_create_training(training_doc)
        return

        for chapter_doc in self.fetch_training_chapter_docs(training_doc):
            chapter = self.get_or_create_chapter(chapter_doc, training)

            for section_doc in self.fetch_training_section_docs(chapter):
                self.get_or_create_section(section_doc, chapter)

        # Create chapter where we relocate top level content
        chapter, _ = models_training.Chapter.objects.get_or_create(
            index=0, training=training, name="Top", slug=f"top-{training.slug}"
        )
        for section_doc in self.fetch_top_level_assets(training_doc):
            self.get_or_create_section(section_doc, chapter)

    def handle(self, *args, **options):

        if options['all']:
            self.console_log("Reconciling all trainings")
            for training_doc in self.fetch_training_docs():
                self.reconcile_training(training_doc)
            return

        for training_slug in options['slugs']:
            training_doc = mongo.projects_collection.find_one(
                {'url': training_slug, '_deleted': {'$ne': True}}
            )
            self.reconcile_training(training_doc)
