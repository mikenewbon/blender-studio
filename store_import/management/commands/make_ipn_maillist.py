"""
Usage:

    DJANGO_SETTINGS_MODULE=studio.settings_store_import ./manage.py make_ipn_maillist
"""
from typing import Tuple, Set
import logging
import re

from django.core.management.base import BaseCommand
import requests.exceptions

from users.blender_id import BIDSession
import store_import.management.commands.utils as utils

bid = BIDSession()
logger = logging.getLogger(__name__)
ids_filename = 'subscriptions_flagged_paypal_ipn.txt'


class Command(BaseCommand):
    """Writes name and emails of people with PayPal IPN subscriptions to a CSV."""

    def _read_ids(self, filename: str) -> Tuple[Set[int], str]:
        _flagged_ids = set()
        try:
            with open(filename, 'r') as f:
                _flagged_ids.update([int(_.strip()) for _ in f.readlines()])
        except FileNotFoundError:
            pass
        return _flagged_ids

    def handle(self, *args, **kwargs):
        """Same as the above."""
        ids = self._read_ids(ids_filename)

        # Subscription ID, customer email, Blender ID email, full name, Blender ID full name:
        paypal_ipn_rows = []
        wp_subscriptions = utils._get_subscriptions(id__in=ids)
        wp_users = utils.get_wp_users(wp_subscriptions)
        for wp_subscription in wp_subscriptions:
            wp_user = wp_users[int(utils._get_meta_value(wp_subscription, '_customer_user'))]
            oauth_user_id = utils._get_meta_value(wp_user, 'blender_id', '').strip()
            first_name = utils._get_meta_value(wp_subscription, 'billing_first_name', '').strip()
            last_name = utils._get_meta_value(wp_subscription, 'billing_last_name', '').strip()
            full_name = ''
            if first_name or last_name:
                full_name = f'{first_name} {last_name}'.strip()
            email = (
                utils._get_meta_value(wp_user, 'billing_email')
                or utils._get_meta_value(wp_subscription, 'billing_email', '').strip()
            )

            blender_id_user = {}
            if oauth_user_id:
                try:
                    blender_id_user = bid.get_user_by_id(oauth_user_id)
                except requests.exceptions.HTTPError:
                    logger.warning(
                        'Unable to get Blender ID data for pk=%s, Blender ID %s',
                        wp_subscription.pk,
                        oauth_user_id,
                    )
            else:
                logger.warning('pk=%s has no Blender ID', wp_subscription.pk)
            blender_id_email = blender_id_user.get('email', '').strip()
            blender_id_full_name = re.sub(
                r'\s\s+', ' ', blender_id_user.get('full_name', '').strip()
            )
            date_deletion_requested = blender_id_user.get('date_deletion_requested', '')
            paypal_ipn_rows.append(
                (
                    wp_subscription.pk,
                    email,
                    blender_id_email if blender_id_email != email else '',
                    full_name,
                    blender_id_full_name if blender_id_full_name != full_name else '',
                    date_deletion_requested,
                    utils._subscription_status(wp_subscription.status),
                    oauth_user_id,
                )
            )

        with open('paypal_ipn_emails.csv', 'w+') as f:
            f.write(
                ';'.join(
                    (
                        '"Subscription ID"',
                        '"Email"',
                        '"Blender ID email"',
                        '"Name"',
                        '"Blender ID name"',
                        '"Deletion requested at"',
                        '"Status"',
                        '"Blender ID"',
                    )
                )
                + '\n'
            )
            f.write(
                '\n'.join(
                    ';'.join(f'"{_ if _ else str()}"' for _ in row) for row in paypal_ipn_rows
                )
            )
