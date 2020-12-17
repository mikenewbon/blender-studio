"""Upserts users to a Mailgun mail list with a given alias."""
from collections import OrderedDict
from typing import List, Tuple, Any
import itertools
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import F
from django.core.paginator import Paginator

from common import mailgun
from common import queries
from profiles.models import Profile

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def chunked(it, size):
    """Iterate over it in chunks of size."""
    it = iter(it)
    while True:
        p = tuple(itertools.islice(it, size))
        if not p:
            break
        yield p


class Command(BaseCommand):
    """Upsert users to a mail list depending on their is_subscribed_to_newsletter."""

    def import_from_csvs(self, *csvs) -> OrderedDict:
        """Read from CSVs."""
        unique_subscribers = OrderedDict()
        weird_records = set()
        for name in csvs:
            with open(name, 'r') as f:
                lines = [_.strip() for _ in f.readlines()]
            for line in lines:
                bits = [_ for _ in line.split(',')]
                full_name = None
                if len(bits) == 2:
                    full_name, email = bits
                elif len(bits) == 1:
                    (email,) = bits
                else:
                    weird_records.add(line)
                    email = bits[-1]
                    full_name = ''.join(bits[:2])
                unique_subscribers[email.strip()] = full_name.strip() if full_name else None
        logger.info(
            'Imported %s total, weird records %s', len(unique_subscribers), len(weird_records)
        )
        for _ in weird_records:
            print(_)
        return unique_subscribers

    def export_to_csvs(self, unique_subscribers: OrderedDict, csvs: List[Tuple[Any]]):
        """Write CSVs."""
        count = 0
        write_to = None
        for _, user in unique_subscribers.items():
            # Switch the file, if necessary
            next_file = None
            for from_count, file_name in csvs:
                if count >= from_count and file_name != write_to.name:
                    next_file = file_name
            if next_file:
                if write_to:
                    write_to.close()
                    logger.info('Done with %s', write_to.name)
                write_to = open(next_file, 'w+')
                logger.info('Opened %s', write_to.name)
            line = f'{user.email}\n'
            if user.profile.full_name:
                line = f'{user.profile.full_name}, {user.email}\n'
            write_to.write(line)
            count += 1
        write_to.close()

    def get_unique_subscribers(self, **filters) -> OrderedDict:
        """Subj."""
        subscribed_users = (
            User.objects.filter(
                profile__is_subscribed_to_newsletter=True,
                **filters,
            )
            .select_related('profile')
            .prefetch_related('groups')
        )

        to_add_to_maillist = subscribed_users.order_by(
            F('groups__name').desc(nulls_last=True),
            F('last_login').desc(nulls_last=True),
        )

        logger.info(
            '%s records to add, first %s, groups: %s',
            Profile.objects.filter(is_subscribed_to_newsletter=True).distinct().count(),
            to_add_to_maillist[0].last_login,
            to_add_to_maillist[0].groups.all(),
        )

        unique_subscribers = OrderedDict()

        p = Paginator(to_add_to_maillist, 600, orphans=0, allow_empty_first_page=False)
        for page_num in range(p.num_pages):
            page = p.get_page(page_num)
            unique_subscribers.update({_.email: _ for _ in page.object_list})
            if page_num and not page_num % 10:
                logger.info(
                    'Page %s/%s (real count: %s)', page_num, p.num_pages, len(unique_subscribers)
                )
                break

        logger.info('Total count: %s', len(unique_subscribers))
        return unique_subscribers

    def _check_missing(self, alias_address):
        csvs = ('newsletter1.csv', 'newsletter2.csv', 'newsletter3.csv')
        unique_subscribers = self.import_from_csvs(*csvs)
        mail_list = mailgun.download_maillist(alias_address, limit=1000)

        expected = set(email for email, _ in unique_subscribers.items())
        found_in_mail_list = set(email for _, email in mail_list)
        return expected.difference(found_in_mail_list)

    def handle(self, *args, **options):  # noqa: D102
        logger.info(
            'Mailgun domain: %s, maillists: %s, %s',
            settings.MAILGUN_SENDER_DOMAIN,
            settings.NEWSLETTER_SUBSCRIBER_LIST,
            settings.NEWSLETTER_NONSUBSCRIBER_LIST,
        )

        unique_subscribers = self.get_unique_subscribers()
        subscribers, non_subscribers = set(), set()
        for u in unique_subscribers.values():
            if queries.has_active_subscription(u):
                subscribers.add(u)
            else:
                non_subscribers.add(u)
        logger.info(
            'Found %s unique recipients for subscribers list, %s rest',
            len(subscribers),
            len(non_subscribers),
        )

        # Fill in the subscribers list
        if settings.NEWSLETTER_SUBSCRIBER_LIST:
            for chunk in chunked(subscribers, 500):
                recipients = ((u.email, u.profile.full_name) for _, u in chunk)
                mailgun.add_to_maillist(settings.NEWSLETTER_SUBSCRIBER_LIST, recipients)
        else:
            logger.warning('No mail list alias configured for subscribers, skipping')

        # Fill in the non-subscribers list
        if settings.NEWSLETTER_NONSUBSCRIBER_LIST:
            for chunk in chunked(non_subscribers, 500):
                recipients = ((u.email, u.profile.full_name) for _, u in chunk)
                mailgun.add_to_maillist(settings.NEWSLETTER_NONSUBSCRIBER_LIST, recipients)
        else:
            logger.warning('No mail list alias configured for non-subscribers, skipping')
