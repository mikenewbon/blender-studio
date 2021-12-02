"""Background tasks for user-related things."""
from datetime import timedelta
from typing import Dict, Any
import logging

from background_task import background
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from common import history
from common import mailgun
from common import queries
from users.blender_id import BIDSession

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
DELETION_DELTA = timedelta(weeks=2)

bid = BIDSession()


@background()
def handle_is_subscribed_to_newsletter(pk: int):
    """Send a request to Mailgun to create or delete an unsubscribe record.

    See https://documentation.mailgun.com/en/latest/api-suppressions.html#unsubscribes
    """
    user = User.objects.get(pk=pk)
    email = user.email

    if user.is_subscribed_to_newsletter:
        recipient = (email, user.full_name)
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
        # Do not create an Unsubscribe records because we still need to send transactional emails!
        # mailgun.create_unsubscribe_record(email)
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
def handle_tracking_event_unsubscribe(event_type: str, message_id: str, event: Dict[str, Any]):
    """Unsubscribe a user from all mail, if one with a matching email is found."""
    event_data = event.get('event-data', {})
    should_unsubscribe = (
        event_type in ('unsubscribed', 'complained')
        or event_type in ('failed', 'bounced')
        and event_data.get('severity') == 'permanent'
    )
    if not should_unsubscribe:
        logger.error('Received an event of an unknown type: id=%s, type=%s', message_id, event_type)
        return

    email = event['event-data']['recipient'].replace('mailto:', '')

    # Must look up emails case-insensitively
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        logger.error(
            'Received an event for an uknown recipient: id=%s, type=%s', message_id, event_type
        )
        return

    change_msg = f'is_subscribed_to_newsletter changed. Reason: {event_type} at Mailgun'
    if 'delivery-status' in event_data:
        delivery_status = event_data['delivery-status']
        delivery_message = delivery_status['message']
        reason = event_data.get('reason', event_type)
        mailing_list = event.get('mailing-list', {}).get('address', '')
        change_msg = (
            'is_subscribed_to_newsletter changed due to permanently failed delivery at Mailgun.'
            f' Reason: {reason}, message: {delivery_message}, list: {mailing_list}'
        )
    with transaction.atomic():
        history.log_change(user, change_msg)
        user.is_subscribed_to_newsletter = False
        user.save(update_fields=['is_subscribed_to_newsletter'])


@background()
def unsubscribe_from_newsletters(pk: int):
    """Remove emails of user with given pk from newsletter lists."""
    user = User.objects.get(pk=pk)
    emails = (user.email, user.customer.billing_email)
    for email in emails:
        if not email:
            continue
        for list_name in (
            settings.NEWSLETTER_SUBSCRIBER_LIST,
            settings.NEWSLETTER_NONSUBSCRIBER_LIST,
        ):
            mailgun.delete_from_maillist(list_name, email)


@background()
def handle_deletion_request(pk: int) -> bool:
    """Delete user account and all data related to it."""
    prior_to = timezone.now() - DELETION_DELTA
    user = User.objects.get(
        date_deletion_requested__isnull=False,
        date_deletion_requested__lt=prior_to,
        pk=pk,
    )

    if not user.can_be_deleted:
        logger.error('Cannot delete user pk=%s', pk)
        return False

    unsubscribe_from_newsletters(pk=pk)

    user.anonymize_or_delete()
    return True


@background()
def grant_blender_id_role(pk: int, role: str, **kwargs) -> bool:
    """Call Blender ID API to grant a given role to a user with given ID."""
    user = User.objects.get(pk=pk)
    bid.grant_revoke_role(user, action='grant', role=role)
    bid.copy_badges_from_blender_id(user=user)
    return True


@background()
def revoke_blender_id_role(pk: int, role: str, **kwargs) -> bool:
    """Call Blender ID API to revoke given roles from a user with given ID."""
    user = User.objects.get(pk=pk)
    bid.grant_revoke_role(user, action='revoke', role=role)
    bid.copy_badges_from_blender_id(user=user)
    return True
