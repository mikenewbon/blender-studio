"""Imports/exports email addresses to/from Mailgun lists/CSVs."""
from collections import OrderedDict
from typing import List, Tuple, Any
import logging
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db.models import Q

from common import mailgun

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


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

    def export_to_csvs(self, unique_subscribers: dict, csvs: List[Tuple[Any]]):
        """Write CSVs."""
        count = 0
        write_to = None
        users = unique_subscribers
        if isinstance(unique_subscribers, dict):
            users = unique_subscribers.values()
        for user in users:
            # Switch the file, if necessary
            next_file = None
            for from_count, file_name in csvs:
                if count >= from_count:
                    next_file = file_name
            if next_file and next_file != getattr(write_to, 'name', None):
                if write_to:
                    write_to.close()
                    logger.info('Done with %s', write_to.name)
                write_to = open(next_file, 'w+')
                logger.info('Opened %s', write_to.name)
            line = f'{user.email}\n'
            if user.full_name:
                line = f'{user.full_name}, {user.email}\n'
            write_to.write(line)
            count += 1
        write_to.close()

    def get_unique_subscribers(self, filters: Q = None, excludes: Q = None) -> OrderedDict:
        """Subj."""
        subscribed_users = User.objects.filter(
            profile__is_subscribed_to_newsletter=True,
        ).prefetch_related('groups')
        if filters:
            subscribed_users = subscribed_users.filter(filters)
        if excludes:
            subscribed_users = subscribed_users.exclude(excludes)

        max_id = subscribed_users.order_by('-id')[0].id
        logger.info('Max ID: %s', max_id)
        unique_subscribers_unordered = {}
        for ids in chunks(range(1, max_id + 100), 1000):
            logger.info('At %s', ids)
            unique_subscribers_unordered.update(
                {_.email: _ for _ in subscribed_users.filter(id__in=ids)}
            )

        logger.info(
            '%s records to add, %s',
            User.objects.filter(is_subscribed_to_newsletter=True).distinct().count(),
            len(unique_subscribers_unordered),
        )
        return unique_subscribers_unordered

    def _sort(self, users: dict):
        def _user_sorting_key(u):
            has_groups = u.groups.count() != 0
            date = u.last_login or u.date_joined
            timestamp = int(time.mktime(date.timetuple())) if date else None
            if has_groups:
                return 10 * timestamp
            return timestamp / 10

        users_sorted = sorted(users.values(), key=_user_sorting_key, reverse=True)
        logger.info(
            'Sorted %s: %s, first user groups: %s',
            len(users_sorted),
            users_sorted[:20],
            users_sorted[0].groups.all(),
        )
        return users_sorted

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
        self._export_non_subscribers_batches()

    def _export_non_subscribers_batches(self):
        perm = Permission.objects.get(codename='can_view_content')
        active_subsriber_q = Q(groups__permissions=perm) | Q(user_permissions=perm)
        non_subscribers = self.get_unique_subscribers(excludes=active_subsriber_q)
        logger.info(
            'Found %s unique recipients non-subscribers list',
            len(non_subscribers),
        )

        logger.info('Sorting..')
        non_subscribers_sorted = self._sort(non_subscribers)
        lists = [
            (0, 'newsletter1.csv'),
            (20000, 'newsletter2.csv'),
            (55000, 'newsletter3.csv'),
        ]
        logger.info('Exporting..')
        self.export_to_csvs(non_subscribers_sorted, lists)

    def _export_subscribers_non_subscribers(self):
        perm = Permission.objects.get(codename='can_view_content')
        active_subsriber_q = Q(groups__permissions=perm) | Q(user_permissions=perm)
        subscribers = self.get_unique_subscribers(filters=active_subsriber_q)
        non_subscribers = self.get_unique_subscribers(excludes=active_subsriber_q)
        logger.info(
            'Found %s unique recipients for subscribers list, %s rest',
            len(subscribers),
            len(non_subscribers),
        )

        self.export_to_csvs(subscribers, [(0, f'{settings.NEWSLETTER_SUBSCRIBER_LIST}.csv')])
        self.export_to_csvs(non_subscribers, [(0, f'{settings.NEWSLETTER_NONSUBSCRIBER_LIST}.csv')])

    def _add_to_maillists(self, subscribers, non_subscribers):
        # Fill in the subscribers list
        if settings.NEWSLETTER_SUBSCRIBER_LIST:
            for chunk in chunks(subscribers, 500):
                recipients = ((u.email, u.full_name) for _, u in chunk)
                mailgun.add_to_maillist(settings.NEWSLETTER_SUBSCRIBER_LIST, recipients)
        else:
            logger.warning('No mail list alias configured for subscribers, skipping')

        # Fill in the non-subscribers list
        if settings.NEWSLETTER_NONSUBSCRIBER_LIST:
            for chunk in chunks(non_subscribers, 500):
                recipients = ((u.email, u.full_name) for _, u in chunk)
                mailgun.add_to_maillist(settings.NEWSLETTER_NONSUBSCRIBER_LIST, recipients)
        else:
            logger.warning('No mail list alias configured for non-subscribers, skipping')
