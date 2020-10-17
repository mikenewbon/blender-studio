import pytz
from django.core.management.base import BaseCommand
from blender_id_oauth_client.models import OAuthUserInfo


class ImportCommand(BaseCommand):
    def console_log(self, message: str):
        self.stdout.write(self.style.NOTICE(message))

    def reconcile_user(self, user, user_doc):
        self.console_log(f"\t Reconciling user {user_doc['username']}")
        user.date_joined = pytz.utc.localize(user_doc['_created'])
        user.save()
        user.profile.full_name = user_doc['full_name']
        if 'settings' in user_doc and 'email_communications' in user_doc['settings']:
            user.profile.is_subscribed_to_newsletter = user_doc['settings']['email_communications']
        user.profile.save()

        if 'auth' in user_doc and user_doc['auth']:
            OAuthUserInfo.objects.get_or_create(
                user=user, oauth_user_id=user_doc['auth'][0]['user_id']
            )
