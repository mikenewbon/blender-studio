from django.contrib.auth.models import User

from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand


class Command(ImportCommand):
    help = 'Import users'


def handle(self, *args, **options):
    for user_doc in mongo.users_collection.find():
        self.stdout.write(self.style.NOTICE(f"Importing user {user_doc['username']}"))
        # Skip Flamenco Manager users
        if user_doc['username'].startswith('SRV-'):
            continue
        try:
            user = User.objects.get(username=user_doc['username'])
            # If force, then update all info
            self.reconcile_user(user, user_doc)
        except User.DoesNotExist:
            user = User.objects.create(username=user_doc['username'], email=user_doc['email'])
            self.reconcile_user(user, user_doc)
