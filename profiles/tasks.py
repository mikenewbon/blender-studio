"""Background tasks for Profile-related things."""
from typing import Dict, Any
import logging

from background_task import background
from django.conf import settings

from common import mailgun
from profiles.models import Profile

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@background()
def handle_is_subscribed_to_newsletter(pk: int):
    """Send a request to Mailgun to create or delete an unsubscribe record.

    See https://documentation.mailgun.com/en/latest/api-suppressions.html#unsubscribes
    """
    profile = Profile.objects.get(pk=pk)
    email = profile.user.email

    unsubscribe_record = mailgun.get_unsubscribe_record(email)

    if profile.is_subscribed_to_newsletter:
        if unsubscribe_record:
            mailgun.delete_unsubscribe_record(email)
        mailgun.add_to_maillist(settings.NEWSLETTER_LIST, [profile.user])
        logger.info('Subscribed %s', profile)
    else:
        if not unsubscribe_record:
            mailgun.create_unsubscribe_record(email)
        mailgun.delete_from_maillist(settings.NEWSLETTER_LIST, email)
        logger.info('Unsubscribed %s', profile)


@background()
def handle_subscribed_unsubscribed_event(event_type: str, message_id: str, event: Dict[str, Any]):
    """Update profile settings in accordance with an unsubscribe event."""
    if event_type not in ('unsubscribed',):
        logger.error('Received an event of an unknown type: id=%s, type=%s', message_id, event_type)
        return

    email = event['event-data']['recipient'].replace('mailto:', '')

    if event_type == 'unsubscribed':
        logger.debug('Unsubscribed %s, %s', message_id, email)
        profile = Profile.objects.filter(user__email=email).first()
        if not profile:
            logger.error(
                'Received an event for an uknown recipient: id=%s, type=%s', message_id, event_type
            )
            return
        profile.is_subscribed_to_newsletter = False
        profile.save(update_fields=['is_subscribed_to_newsletter'])
