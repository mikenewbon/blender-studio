"""Background tasks for Profile-related things."""
import logging

from background_task import background
from django.conf import settings

from common import mailgun
from profiles.models import Profile

logger = logging.getLogger(__name__)


@background()
def handle_is_subscribed_to_newsletter(pk: int):
    """Send a request to Mailgun to create or delete an unsubscribe record.

    See https://documentation.mailgun.com/en/latest/api-suppressions.html#unsubscribes
    """
    profile = Profile.objects.get(pk=pk)
    email = profile.user.email

    if profile.is_subscribed_to_newsletter:
        mailgun.delete_unsubscribe_record(email)
        mailgun.add_to_maillist(settings.NEWSLETTER_LIST, [profile.user])
        logger.info('Subscribed %s', profile)
    else:
        mailgun.create_unsubscribe_record(email)
        mailgun.delete_from_maillist(settings.NEWSLETTER_LIST, email)
        logger.info('Unsubscribed %s', profile)
