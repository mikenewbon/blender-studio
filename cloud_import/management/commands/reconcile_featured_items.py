import datetime
import os
import pathlib
import shutil
import pytz
from bson import json_util, ObjectId

from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings


from cloud_import.management import mongo
import comments.models as models_comments
import films.models as models_films
import static_assets.models as models_static_assets
from cloud_import.management.mixins import ImportCommand
from cloud_import.management import files
import training.models as models_training


class Command(ImportCommand):
    help = 'Reconcile featured assets and sections'

    def handle(self, *args, **options):
        for film in models_films.Film.objects.all():
            film_doc = mongo.projects_collection.find_one(
                {'url': film.slug, 'nodes_featured': {'$exists': True, '$ne': []}}
            )
            for node_featured_id in film_doc['nodes_featured']:
                asset = models_films.Asset.objects.get(slug=str(node_featured_id))
                asset.is_featured = True
                asset.save()

        for training in models_training.Training.objects.all():
            training_doc = mongo.projects_collection.find_one(
                {'url': training.slug, 'nodes_featured': {'$exists': True, '$ne': []}}
            )
            if not training_doc:
                continue
            for node_featured_id in training_doc['nodes_featured']:
                try:
                    section = models_training.Section.objects.get(slug=str(node_featured_id))
                except models_training.Section.DoesNotExist:
                    continue
                section.is_featured = True
                section.save()
