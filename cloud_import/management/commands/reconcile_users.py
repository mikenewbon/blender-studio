import pymongo

from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand


class Command(ImportCommand):
    help = 'Reconcile users'

    def add_arguments(self, parser):
        parser.add_argument('-u', '--user', dest='users', action='append', help="Provide usernames")
        parser.add_argument(
            '--all', action='store_true', help='Reconcile all users',
        )

    def reconcile_user_with_view_progress(self, user_doc):
        # self.stdout.write(self.style.NOTICE(f"Importing user {user_doc['username']}"))
        # Skip Flamenco Manager users
        if user_doc['username'].startswith('SRV-'):
            return
        self.console_log(f"-- Processing user {user_doc['username']}")
        user = self.get_or_create_user(user_doc['_id'])
        self.console_log(f"-- Processing view progress for user {user_doc['username']}")
        self.reconcile_user_view_progress(user, user_doc)

    def handle(self, *args, **options):
        if options['all']:
            mongo.users_collection.create_index([('_updated', pymongo.DESCENDING)])
            for user_doc in mongo.users_collection.find({'_deleted': {'$ne': True}}).sort(
                '_updated', pymongo.DESCENDING
            ):
                self.reconcile_user_with_view_progress(user_doc)
            return

        for username in options['users']:
            user_doc = mongo.users_collection.find_one(
                {'username': username, '_deleted': {'$ne': True}}
            )
            self.reconcile_user_with_view_progress(user_doc)
