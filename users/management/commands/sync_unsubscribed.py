"""Unsubscribes users who's emails permanently failed for some reason at Mailgun."""
import logging

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

import users.tasks as tasks

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
    """Create Mailgun unsubscribes for users who have is_subscribed_to_newsletter==False."""

    def handle(self, *args, **options):  # noqa: D102
        unsubscribed_users = User.objects.filter(is_subscribed_to_newsletter=False)
        logger.info(
            'Mailgun domain: %s, maillists: %s, %s, total unsubscribed: %s',
            settings.MAILGUN_SENDER_DOMAIN,
            settings.NEWSLETTER_SUBSCRIBER_LIST,
            settings.NEWSLETTER_NONSUBSCRIBER_LIST,
            unsubscribed_users.count(),
        )
        return
        for user in unsubscribed_users:
            tasks.handle_is_subscribed_to_newsletter(pk=user.pk)
