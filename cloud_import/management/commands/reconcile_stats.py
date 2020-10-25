import pytz
import datetime

from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand

from stats.models import Sample


class Command(ImportCommand):
    help = 'Reconcile stats'

    def reconcile_sample_set(self, stat_doc):
        def safeget(dct, *keys):
            for key in keys:
                try:
                    dct = dct[key]
                except KeyError:
                    return None
            return dct

        try:
            Sample.objects.get(legacy_id=str(stat_doc['_id']))
            self.console_log(f"Record for {stat_doc['_id']} exists")
        except Sample.DoesNotExist:
            if isinstance(stat_doc['timestamp'], str):
                # 2017-07-23T00:00:00
                stat_doc['timestamp'] = datetime.datetime.strptime(
                    stat_doc['timestamp'][:19], '%Y-%m-%dT%H:%M:%S'
                )

            try:
                Sample.objects.create(
                    legacy_id=str(stat_doc['_id']),
                    timestamp=pytz.utc.localize(stat_doc['timestamp']),
                    comments_count=safeget(
                        stat_doc, 'nodes', 'public_node_count_per_type', 'comment'
                    ),
                    blog_posts_count=safeget(
                        stat_doc, 'nodes', 'public_node_count_per_type', 'post'
                    ),
                    users_total_count=safeget(stat_doc, 'users', 'total_real_user_count'),
                    users_subscribers_count=safeget(
                        stat_doc, 'users', 'count_per_type', 'subscriber'
                    ),
                    users_demo_count=safeget(stat_doc, 'users', 'count_per_type', 'demo'),
                )
                self.console_log(f"Created record for {stat_doc['_id']}")
            except KeyError as k:
                print(k)
                self.console_log(f"Failed to create record for {stat_doc['_id']}")

    def handle(self, *args, **options):
        for sample in mongo.stats_collection.find():
            self.reconcile_sample_set(sample)
