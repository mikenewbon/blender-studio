from typing import Optional, Union
import datetime
import os
import pathlib
import pprint
import pytz
import re
import shutil
import tempfile

from bson import json_util, ObjectId
from django.core.management.base import BaseCommand
from django.core.files import File
from django.contrib.auth import get_user_model
from django.db.models import signals
import factory

from cloud_import.management import mongo

import films.models as models_films
import static_assets.models as models_assets
from cloud_import.management.mixins import ImportCommand
from characters.models import (
    Character,
    CharacterVersion,
    CharacterVersionComment,
    CharacterShowcase,
    CharacterShowcaseComment,
    BlenderVersion,
)

DEFAULT_MIN_VERSION = BlenderVersion.v280
User = get_user_model()
RAIN_SHOWCASE = "5f1ede754347a0fc05ba21a0"
RAIN_SLUGS = (
    "5dd54d68a709ab2eb08aa5a1",
    "5f04a68bb5f1a2612f7b29da",
    RAIN_SHOWCASE,
)
RAIN_SLUG = '5f1ed640e9115ed35ea4b3fb'


def _parse_min_version_from(value: str) -> Optional[str]:
    # e.g. For Blender 2.8x Eevee and Cycles
    m = re.match(r'blender.*(\d\.\d{1,2}).*', value, re.I)
    if m:
        return m.groups()[0]
    return DEFAULT_MIN_VERSION


def _parse_number_from(value: str) -> Optional[str]:
    # e.g. Rain v1.0
    m = re.match(r'.*\s+v(\d\.\d{1,2}).*', value, re.I)
    if m:
        return int(float(m.groups()[0]))
    return 1


class Command(ImportCommand):
    help = 'Reconcile training data'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slug', dest='slugs', action='append', help="provides training slugs"
        )
        parser.add_argument('--all', action='store_true', help='Reconcile all trainings')

    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def reconcile_character_comments(
        self, version_or_showcase: Union[CharacterVersion, CharacterShowcase], doc_version
    ):
        is_showcase = isinstance(version_or_showcase, CharacterShowcase)
        # Fetch comments
        comments = mongo.nodes_collection.find(
            {
                'node_type': 'comment',
                '_deleted': {'$ne': True},
                'parent': doc_version['_id'],
                'properties.status': 'published',
            }
        )
        m2m = CharacterShowcaseComment if is_showcase else CharacterVersionComment
        comments_count = 0
        for comment_doc in comments:
            self.console_log(
                f"Processing comment {comment_doc['_id']} for asset {version_or_showcase.id}"
            )
            comment = self.get_or_create_comment(comment_doc)
            kwargs = {'comment': comment}
            if is_showcase:
                kwargs['character_showcase'] = version_or_showcase
            else:
                kwargs['character_version'] = version_or_showcase
            m2m.objects.get_or_create(**kwargs)
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
                kwargs = {'comment': reply_comment}
                if is_showcase:
                    kwargs['character_showcase'] = version_or_showcase
                else:
                    kwargs['character_version'] = version_or_showcase
                m2m.objects.get_or_create(**kwargs)
                self.reconcile_comment_ratings(reply_comment_doc)

        if comments_count > 0:
            self.console_log(f"Processed {comments_count} comments")

    def _get_or_create_character(self, character_doc, **kargs) -> Character:
        try:
            character = Character.objects.get(slug=character_doc['_id'])
        except Character.DoesNotExist:
            self.console_log(f"Character {character_doc['_id']} does not exist")
            character = Character.objects.create(
                name=character_doc['name'], slug=character_doc['_id']
            )
        character.is_published = character_doc['properties']['status'] == 'published'
        character.date_created = pytz.utc.localize(character_doc['_created'])
        character.date_published = pytz.utc.localize(character_doc['_created'])
        character.date_updated = pytz.utc.localize(character_doc['_updated'])
        character.save()
        return character

    def _get_or_create_character_version(
        self, character: Character, version_doc
    ) -> CharacterVersion:
        pprint.pprint(version_doc)
        file_doc = mongo.files_collection.find_one(
            {'_id': ObjectId(version_doc['properties']['file'])}
        )
        static_asset = self.get_or_create_static_asset(file_doc, thumbnail_file_doc=None)

        number = _parse_number_from(version_doc['name'])
        character_version, _ = CharacterVersion.objects.get_or_create(
            character=character, number=number, static_asset=static_asset
        )
        character_version.description = version_doc['description']
        character_version.is_published = version_doc['properties']['status'] == 'published'
        character_version.is_free = version_doc.get('permissions', {}).get('world') == ['GET']
        character_version.min_blender_version = _parse_min_version_from(version_doc['description'])
        character_version.date_created = pytz.utc.localize(version_doc['_created'])
        character_version.date_updated = pytz.utc.localize(version_doc['_updated'])
        character_version.date_published = pytz.utc.localize(version_doc['_created'])

        # Ensure media
        if 'picture' in version_doc:
            self.reconcile_file_field(
                version_doc['picture'], character_version.static_asset, 'thumbnail'
            )
        character_version.save()

        self.reconcile_character_comments(character_version, version_doc)

        return character_version

    def _get_or_create_character_showcase(self, character: Character, version_doc):
        pprint.pprint(version_doc)
        file_doc = mongo.files_collection.find_one(
            {'_id': ObjectId(version_doc['properties']['file'])}
        )
        static_asset = self.get_or_create_static_asset(file_doc, thumbnail_file_doc=None)

        showcase, _ = CharacterShowcase.objects.get_or_create(
            character=character, static_asset=static_asset
        )
        showcase.description = version_doc['description']
        showcase.is_published = version_doc['properties']['status'] == 'published'
        showcase.is_free = version_doc.get('permissions', {}).get('world') == ['GET']
        showcase.title = version_doc['name']
        showcase.min_blender_version = _parse_min_version_from(version_doc['description'])
        showcase.date_created = pytz.utc.localize(version_doc['_created'])
        showcase.date_updated = pytz.utc.localize(version_doc['_updated'])

        # Ensure media
        if 'picture' in version_doc:
            self.reconcile_file_field(version_doc['picture'], showcase.static_asset, 'thumbnail')
        showcase.save()

        self.reconcile_character_comments(showcase, version_doc)

        return showcase

    def fetch_character_docs(self, slugs=None):
        """Get all characters from mongoDB."""
        characters_projects = mongo.projects_collection.find({'url': 'characters'})
        for character_project in characters_projects:
            characters = mongo.nodes_collection.find(
                {
                    '$or': [
                        {
                            'project': character_project['_id'],
                            '_deleted': {'$ne': True},
                            'node_type': 'asset',
                            'properties.status': 'published',
                        },
                        {
                            'project': character_project['_id'],
                            '_deleted': {'$ne': True},
                            'node_type': 'group',
                            'properties.status': 'published',
                        },
                    ]
                },
            )
            for doc in characters:
                if slugs and str(doc['_id']) not in slugs:
                    # Skip if particular character slugs are given, and this is not one of them
                    continue
                if self._is_archived(doc):
                    # Skip archived character
                    self.console_log(f"{doc['_id']} is in archived character, skipping")
                    continue
                yield doc

    def _is_archived(self, doc) -> bool:
        if 'parent' not in doc:
            return False
        parent = next(mongo.nodes_collection.find({'_id': doc['parent']}), None)
        if parent and parent['name'] == 'archived':
            return True
        return self._is_archived(parent)

    def process_character_doc(self, character_doc) -> Character:
        str_slug = str(character_doc['_id'])
        if str_slug in RAIN_SLUGS:
            self.console_log(
                f"Skipping Rain version {character_doc['_id']}, should be handled via group"
            )
            return

        self.console_log(f"Handling character character_doc {character_doc['_id']}")
        self.count += 1

        character = self._get_or_create_character(character_doc)

        has_multiple_versions = character_doc['node_type'] == 'group'
        if not has_multiple_versions:
            self._get_or_create_character_version(character, character_doc)
            return character

        version_docs = mongo.nodes_collection.find({'parent': character_doc['_id']})
        for doc_version in version_docs:
            if str(doc_version['_id']) == RAIN_SHOWCASE:
                self._get_or_create_character_showcase(character, doc_version)
            else:
                self._get_or_create_character_version(character, doc_version)
        return character

    def handle(self, *args, **options):
        self.count = 0
        if options.get('slugs'):
            self.console_log(f"Importing characters with the following slugs: {options['slugs']}")
        elif options.get('all'):
            self.console_log("Importing all characters")
        else:
            return

        selected_slugs = None if options['all'] else options['slugs']
        for doc in self.fetch_character_docs(slugs=selected_slugs):
            self.process_character_doc(doc)
        self.console_log(f'Found {self.count} characters total')
