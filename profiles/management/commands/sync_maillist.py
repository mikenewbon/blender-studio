"""Upserts users to a Mailgun mail list with a given alias."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from common import mailgun

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Upsert users to a mail list depending on their is_subscribed_to_newsletter."""

    def add_arguments(self, parser):
        """Add mail list alias as a parameter."""
        parser.add_argument('alias_address', type=str)

    def handle(self, *args, **options):  # noqa: D102
        alias_address = options['alias_address']
        logger.info(
            'Mailgun domain: %s, maillist: %s',
            settings.MAILGUN_SENDER_DOMAIN,
            alias_address,
        )
        all_users = User.objects.select_related('profile')
        # FIXME: remove test filters
        all_users = all_users.filter(email__contains='@blender.org').filter(email__contains='anna+')
        to_remove_from_maillist = all_users.filter(profile__is_subscribed_to_newsletter=False)
        to_remove_from_maillist_total = to_remove_from_maillist.count()

        to_add_to_maillist = all_users.filter(profile__is_subscribed_to_newsletter=True)
        to_add_to_maillist_total = to_add_to_maillist.count()

        logger.info(
            '%s records to add, %s to remove',
            to_add_to_maillist_total,
            to_remove_from_maillist_total,
        )

        count = 0
        for user in to_remove_from_maillist.all():
            mailgun.delete_from_maillist(alias_address, user.email)
            mailgun.create_unsubscribe_record(user.email)
            count += 1
            if not count % 1000:
                logger.info('Removed %s/%s', count, to_remove_from_maillist_total)

        offset, limit = 0, 250
        users_q = to_add_to_maillist
        while users_q.count():
            users_q = to_add_to_maillist[offset : offset + limit]
            mailgun.add_to_maillist(alias_address, users_q)
            # There are no unsubscribes at the moment, so delete_unsubscribe_record is not needed
            offset += limit
            if not offset % 1000:
                logger.info('Added %s/%s', count, to_remove_from_maillist_total)
