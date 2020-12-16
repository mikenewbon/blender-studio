"""Upserts users to a Mailgun mail list with a given alias."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import F

from common import mailgun

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Upsert users to a mail list depending on their is_subscribed_to_newsletter."""

    def handle(self, *args, **options):  # noqa: D102
        alias_address = 'newsletter1@blender.cloud'
        logger.info(
            'Mailgun domain: %s, maillist: %s',
            settings.MAILGUN_SENDER_DOMAIN,
            alias_address,
        )
        all_users = User.objects.select_related('profile').prefetch_related('groups')

        to_add_to_maillist = all_users.filter(profile__is_subscribed_to_newsletter=True,).order_by(
            F('groups__name').desc(nulls_last=True),
            F('last_login').desc(nulls_last=True),
        )
        to_add_to_maillist_total = to_add_to_maillist.count()

        logger.info(
            '%s records to add, first %s, groups: %s',
            to_add_to_maillist_total,
            to_add_to_maillist[0].last_login,
            to_add_to_maillist[0].groups.all(),
        )

        offset, limit = 0, 500
        offset_per_list = (
            (15000, 'newsletter2@blender.cloud'),
            (60000, 'newsletter3@blender.cloud'),
        )
        users_q = to_add_to_maillist
        seen_ids = set()
        while users_q.count():
            users_q = to_add_to_maillist[offset : offset + limit]
            mailgun.add_to_maillist(alias_address, users_q)
            seen_ids.update(_.pk for _ in users_q)
            offset += limit
            if not offset % 5000:
                logger.info(
                    'Offset %s to %s (real count: %s)', offset, alias_address, len(seen_ids)
                )
            # Change the list
            new_list = None
            for k, l in offset_per_list:
                if len(seen_ids) > k:
                    new_list = l
            if new_list and new_list != alias_address:
                logger.info('Switching to from list %s to list %s', alias_address, new_list)
                alias_address = new_list
