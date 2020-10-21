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
        parser.add_argument(
            '--force', action='store_true', help='Force update',
        )

    def reconcile_user_with_view_progress(self, user_doc, is_forced):
        # self.stdout.write(self.style.NOTICE(f"Importing user {user_doc['username']}"))
        # Skip Flamenco Manager users
        if user_doc['username'].startswith('SRV-'):
            return
        self.console_log(f"-- Processing user {user_doc['username']}")
        user, is_created = self.get_or_create_user(user_doc['_id'])
        if not is_created:
            self.console_log(f"User {user_doc['username']} already exists")
            if not is_forced:
                return
        self.console_log(f"-- Processing view progress for user {user_doc['username']}")
        self.reconcile_user_view_progress(user, user_doc)

    def handle(self, *args, **options):
        is_forced = options['force']
        if options['all']:
            mongo.users_collection.create_index([('_updated', pymongo.DESCENDING)])
            # Disable cursor timeout for this query, as it take several minutes to run
            cursor = mongo.users_collection.find(
                {'_deleted': {'$ne': True}}, no_cursor_timeout=True
            ).sort('_updated', pymongo.DESCENDING)
            for user_doc in cursor:
                self.reconcile_user_with_view_progress(user_doc, is_forced)
            cursor.close()
            return

        for username in options['users']:
            user_doc = mongo.users_collection.find_one(
                {'username': username, '_deleted': {'$ne': True}}
            )
            self.reconcile_user_with_view_progress(user_doc, is_forced)
