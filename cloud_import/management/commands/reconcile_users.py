from django.contrib.auth.models import User

from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand


class Command(ImportCommand):
    help = 'Reconcile users'

    def handle(self, *args, **options):
        for user_doc in mongo.users_collection.find({'_deleted': {'$ne': True}}):
            # self.stdout.write(self.style.NOTICE(f"Importing user {user_doc['username']}"))
            # Skip Flamenco Manager users
            if user_doc['username'].startswith('SRV-'):
                continue
            user = self.get_or_create_user(user_doc['_id'])
            self.reconcile_user_view_progress(user, user_doc)
