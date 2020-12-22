"""Background tasks for user-related things."""
from typing import Dict, Any
import logging

from background_task import background
from django.conf import settings
from django.contrib.auth import get_user_model

from common import mailgun
from common import queries

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@background()
def handle_is_subscribed_to_newsletter(pk: int):
    """Send a request to Mailgun to create or delete an unsubscribe record.

    See https://documentation.mailgun.com/en/latest/api-suppressions.html#unsubscribes
    """
    user = User.objects.get(pk=pk)
    email = user.email

    unsubscribe_record = mailgun.get_unsubscribe_record(email)

    if user.is_subscribed_to_newsletter:
        recipient = (email, user.full_name)
        if unsubscribe_record:
            mailgun.delete_unsubscribe_record(email)
        if settings.NEWSLETTER_LIST:
            mailgun.add_to_maillist(settings.NEWSLETTER_LIST, [recipient])

        is_subscriber = queries.has_active_subscription(user)
        if is_subscriber:
            # Also add to subscribers list and remove from non-subscribers one
            add_to = settings.NEWSLETTER_SUBSCRIBER_LIST
            remove_from = settings.NEWSLETTER_NONSUBSCRIBER_LIST
        else:
            # Remove from subscribers list and add to non-subscribers list
            add_to = settings.NEWSLETTER_NONSUBSCRIBER_LIST
            remove_from = settings.NEWSLETTER_SUBSCRIBER_LIST
        if add_to:
            mailgun.add_to_maillist(add_to, [recipient])
        if remove_from:
            mailgun.delete_from_maillist(remove_from, email)
        logger.info('Updated newsletter subscription for user %s', user)
    else:
        if not unsubscribe_record:
            mailgun.create_unsubscribe_record(email)
        for alias_address in (
            settings.NEWSLETTER_LIST,
            settings.NEWSLETTER_SUBSCRIBER_LIST,
            settings.NEWSLETTER_NONSUBSCRIBER_LIST,
        ):
            if not alias_address:
                continue
            mailgun.delete_from_maillist(alias_address, email)
        logger.info('Unsubscribed user %s from all newsletters', user)


@background()
def handle_subscribed_unsubscribed_event(event_type: str, message_id: str, event: Dict[str, Any]):
    """Update user settings in accordance with an unsubscribe event."""
    if event_type not in ('unsubscribed',):
        logger.error('Received an event of an unknown type: id=%s, type=%s', message_id, event_type)
        return

    email = event['event-data']['recipient'].replace('mailto:', '')

    if event_type == 'unsubscribed':
        logger.debug('Unsubscribed %s, %s', message_id, email)
        # Must look up emails case-insensitively
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            logger.error(
                'Received an event for an uknown recipient: id=%s, type=%s', message_id, event_type
            )
            return
        user.is_subscribed_to_newsletter = False
        user.save(update_fields=['is_subscribed_to_newsletter'])
