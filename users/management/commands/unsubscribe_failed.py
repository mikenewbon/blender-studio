"""Unsubscribes users who's emails permanently failed for some reason at Mailgun."""
import json
import logging
import time

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from common import mailgun

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _log_history(who, what, msg: str):
    LogEntry.objects.log_action(
        user_id=who.pk,
        content_type_id=ContentType.objects.get_for_model(what).pk,
        object_id=what.pk,
        object_repr=str(what),
        action_flag=CHANGE,
        change_message=msg,
    )


class Command(BaseCommand):
    """Unsubscribes users who's email turned up in a failed events at Mailgun."""

    def handle(self, *args, **options):  # noqa: D102
        # `LogEntry`'s require a user
        actor = User.objects.filter(id=1, is_superuser=True).first()
        assert actor
        logger.info(
            'Mailgun domain: %s, maillists: %s, %s, admin: %s',
            settings.MAILGUN_SENDER_DOMAIN,
            settings.NEWSLETTER_SUBSCRIBER_LIST,
            settings.NEWSLETTER_NONSUBSCRIBER_LIST,
            actor,
        )
        failed_events = mailgun.download_events(
            event='failed',
            severity='permanent',
            limit=300,
        )
        logger.info('Found %s events', len(failed_events))
        with open(f'mailgun_events_{int(time.time())}.json', 'w+') as f:
            f.write(json.dumps(failed_events))
        count = 0
        for event in failed_events:
            if event['severity'] != 'permanent':
                continue
            email = event['recipient']
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                logger.warning('User with email %s not found', email)
                continue
            if not user.is_subscribed_to_newsletter:
                continue
            delivery_status = event['delivery-status']
            delivery_message = delivery_status['message']
            reason = event['reason']
            mailing_list = event.get('mailing-list', {}).get('address', 'No mailing list')
            change_msg = (
                'is_subscribed_to_newsletter changed due to permanently failed delivery.'
                f'Reason: {reason}, message: {delivery_message}, list: {mailing_list}'
            )
            _log_history(actor, user, change_msg)
            logger.warning('Updating %s due to %s', user, change_msg)
            user.is_subscribed_to_newsletter = False
            user.save(update_fields=['is_subscribed_to_newsletter'])
            count += 1
        logger.info('Updated %s users', count)
