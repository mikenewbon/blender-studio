import datetime
import os
import pathlib
import shutil
import pprint

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware as _make_aware
import dateutil.parser
import pymongo
import pytz

from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand
from stats.models import Sample

User = get_user_model()

"""
{'_id': 'AV6WJaiYyS6gf1Jm5Zvl',
 'files': {'expired_link_count': 5963.0,
           'file_count_per_backend': {'gcs': 24292.0, 'pillar': 1775.0},
           'file_count_per_status': {'-none-': 5188.0,
                                     'complete': 20613.0,
                                     'failed': 31.0,
                                     'processing': 3.0,
                                     'queued_for_processing': 223.0,
                                     'uploading': 9.0},
           'file_count_total': 26067.0,
           'no_link_count': 4885.0,
           'total_bytes_storage_used': 687788320723.0,
           'total_bytes_storage_used_per_backend': {'gcs': 686134521626.0,
                                                    'pillar': 1653799097.0}},
 'nodes': {'public_node_count_per_type': {'asset': 3080.0,
                                          'attract_asset': 59.0,
                                          'attract_shot': 149.0,
                                          'attract_task': 684.0,
                                          'blog': 6.0,
                                          'comment': 3220.0,
                                          'group': 837.0,
                                          'group_hdri': 7.0,
                                          'group_texture': 41.0,
                                          'hdri': 135.0,
                                          'page': 4.0,
                                          'post': 166.0,
                                          'storage': 1.0,
                                          'texture': 1008.0},
           'total_public_node_count': 9397.0},
 'projects': {'home_project_count': 3931.0,
              'private_count': 782.0,
              'public_count': 34.0,
              'total_count': 4747.0,
              'total_deleted_count': 116.0},
 'stats_schema_version': 1.0,
 'timestamp': '2017-09-18T18:00:01.82315871Z',
 'users': {'blender_sync_count': 1194.0,
           'count_per_type': {'demo': 91.0,
                              'service': 103.0,
                              'subscriber': 3004.0},
           'subscriber_count': 3304.0,
           'total_real_user_count': 20488.0,
           'total_user_count': 20591.0}}

"""


def _turn_off_auto_now_add(ModelClass, field_name):
    def auto_now_add_off(field):
        field.auto_now_add = False

    _modify_model_field(ModelClass, field_name, auto_now_add_off)


def _modify_model_field(ModelClass, field_name, func):
    field = ModelClass._meta.get_field(field_name)
    func(field)


_turn_off_auto_now_add(Sample, 'timestamp')


def make_aware(value):
    """Catch AmbiguousTimeError and try with a DST flag."""
    if isinstance(value, str):
        value = dateutil.parser.parse(value)
    try:
        return _make_aware(value)
    except ValueError:
        return value
    except (pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError):
        # , get_current_timezone(), is_dst=False ?
        return _make_aware(value, is_dst=False)


class Command(ImportCommand):
    help = 'Import cloud stats from MongoDB'

    def _copy_stat_doc(self, doc):
        timestamp = make_aware(doc['timestamp'])
        legacy_id = doc['_id']

        if 'public_node_count_per_type' in doc['nodes']:
            if 'comment' in doc['nodes']['public_node_count_per_type']:
                self.samples_to_upsert.append(
                    Sample(
                        timestamp=timestamp,
                        slug='comments_count',
                        value=doc['nodes']['public_node_count_per_type']['comment'],
                        legacy_id=legacy_id,
                    )
                )
            if 'asset' in doc['nodes']['public_node_count_per_type']:
                self.samples_to_upsert.append(
                    Sample(
                        timestamp=timestamp,
                        value=doc['nodes']['public_node_count_per_type']['asset'],
                        slug='film_assets_count',
                        legacy_id=legacy_id,
                    )
                )
        total_user_count = doc['users'].get(
            'total_real_user_count', doc['users'].get('total_user_count')
        )
        if total_user_count:
            self.samples_to_upsert.append(
                Sample(
                    timestamp=timestamp,
                    slug='users_total_count',
                    value=total_user_count,
                    legacy_id=legacy_id,
                )
            )
        # subscriber_count = 'count_per_type' in doc['users'] \
        #    and doc['users']['count_per_type']['subscriber'] \
        #    or doc['users'].get('subscriber_count')
        subscriber_count = doc['users'].get('subscriber_count')
        if subscriber_count is not None:
            self.samples_to_upsert.append(
                Sample(
                    timestamp=timestamp,
                    slug='users_subscribers_count',
                    value=subscriber_count,
                    legacy_id=legacy_id,
                )
            )
        if 'posts' in doc['nodes']['public_node_count_per_type']:
            self.samples_to_upsert.append(
                Sample(
                    timestamp=timestamp,
                    slug='blog_posts_count',
                    value=doc['nodes']['public_node_count_per_type']['post'],
                    legacy_id=legacy_id,
                )
            )
        if 'count_per_type' in doc['users'] and 'demo' in doc['users']['count_per_type']:
            self.samples_to_upsert.append(
                Sample(
                    timestamp=timestamp,
                    slug='users_demo_count',
                    value=doc['users']['count_per_type']['demo'],
                    legacy_id=legacy_id,
                )
            )

    def handle(self, *args, **options):
        cloudstats = mongo.stats_collection
        self.samples_to_upsert = []
        for doc in cloudstats.find():
            try:
                self._copy_stat_doc(doc)
            except Exception:
                pprint.pprint(doc)
                raise

        # upsert the results
        samples_to_update = []
        samples_to_insert = []
        for s in self.samples_to_upsert:
            existing = Sample.objects.filter(timestamp=s.timestamp, slug=s.slug).first()
            if existing:
                s.pk = existing.pk
                samples_to_update.append(s)
            else:
                samples_to_insert.append(s)
        print(len(samples_to_update), 'samples to update')
        print(len(samples_to_insert), 'samples to insert')
        Sample.objects.bulk_update(
            samples_to_update, fields={'timestamp', 'slug', 'legacy_id', 'value'}, batch_size=700
        )
        Sample.objects.bulk_create(samples_to_insert, batch_size=700)
