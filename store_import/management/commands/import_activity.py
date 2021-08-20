"""Import LogEntries from a backup Store database."""
from typing import List
import logging
import time

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from wordpress.models import Post

from looper.models import Subscription

from users.blender_id import BIDSession
import store_import.management.commands.mixins as mixins
import store_import.management.commands.utils as utils

logger = logging.getLogger('store_import')
bid = BIDSession()
User = get_user_model()


# How many WC subscriptions to retrieve in one go (takes a lot of mem)
READ_LIMIT = 700  # 1k older subscriptions w/orders can take over 4GB, cannot use 1k in prod.
# How many "looper" subscriptions to insert in one go
BATCH_SIZE = 300


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]  # noqa: E203


class Command(mixins._UpsertLogEntriesMixin, BaseCommand):
    """Import "Activity" as LogEntries from Store database."""

    help = 'Import "Activity" as LogEntries from Store database.'
    BATCH_SIZE = BATCH_SIZE

    def _construct_subscription_orders_log(
        self,
        wp_subscription: Post,
        subscription: Subscription,
    ) -> List[LogEntry]:
        subscr_id = wp_subscription.id
        log_entries = []
        wp_order = wp_subscription.parent
        order = subscription.order_set.filter(id=wp_order.id).first()
        if order is not None:
            log_entries.extend(
                utils._construct_log_entries_from_comments(
                    wp_order, instance=order, wp_users=self.wp_users
                )
            )
        wp_orders = self.wp_subscription_orders.get(subscr_id, [])
        logger.debug('Orders for %s: %s', wp_subscription, len(wp_orders))
        for wp_order in wp_orders:
            order = subscription.order_set.filter(id=wp_order.id).first()
            if order is None:
                continue
            log_entries.extend(
                utils._construct_log_entries_from_comments(
                    wp_order,
                    instance=order,
                    wp_users=self.wp_users,
                )
            )
        return log_entries

    def handle(self, *args, **options):
        """Import subscriptions and orders data from a backup Store database."""
        start_t = time.time()
        logger.setLevel(logging.INFO)
        # logger.setLevel(logging.DEBUG)

        self._reset()
        self.subscriptions_handled_count = 0
        self.subscriptions = Subscription.objects.filter(is_legacy=True)
        legacy_subscription_ids = set(_.id for _ in self.subscriptions)

        all_wp_subscriptions_q = utils._get_subscriptions(id__in=legacy_subscription_ids)
        # Cannot chunk a set, using list instead
        self.all_wp_subscriptions_ids = [
            int(_['id']) for _ in all_wp_subscriptions_q.values('id').distinct()
        ]
        self.min_subscription_id = min(self.all_wp_subscriptions_ids)
        self.max_subscription_id = max(self.all_wp_subscriptions_ids)
        self.total_count = len(self.all_wp_subscriptions_ids)
        self.wp_users = {}
        logger.info(
            'Min subscription ID %s, max subscription ID %s, total count %s',
            self.min_subscription_id,
            self.max_subscription_id,
            self.total_count,
        )

        for ids in chunks(self.all_wp_subscriptions_ids, READ_LIMIT):
            try:
                self._handle_chunk(ids)
            except Exception:
                break
            except KeyboardInterrupt:
                break

        logger.info(
            'Took %s to finish, subscriptions handled: %s/%s',
            time.time() - start_t,
            self.subscriptions_handled_count,
            self.total_count,
        )

    def _handle_chunk(self, wp_subscriptions_ids):
        start_t = time.time()
        wp_subscriptions_q = utils._get_subscriptions(id__in=wp_subscriptions_ids)

        self.wp_subscription_orders = utils._get_subscriptions_orders(wp_subscriptions_ids)
        count_orders = sum(len(order_list) for order_list in self.wp_subscription_orders.values())
        self.wp_subscriptions = wp_subscriptions_q.all()
        logger.info(
            '%s/%s subscriptions (IDs %s-%s), with %s orders',
            len(wp_subscriptions_ids),
            self.total_count,
            min(wp_subscriptions_ids),
            max(wp_subscriptions_ids),
            count_orders,
        )

        for wp_subscription in self.wp_subscriptions:
            try:
                subscription = self.subscriptions.get(id=wp_subscription.pk)
                self.log_entries_to_upsert.extend(
                    utils._construct_log_entries_from_comments(
                        wp_subscription, instance=subscription, wp_users=self.wp_users
                    )
                )
                self.log_entries_to_upsert.extend(
                    self._construct_subscription_orders_log(wp_subscription, subscription)
                )
                self.subscriptions_handled_count += 1
                # FIXME(anna): uncomment to insert the data
                # self._upsert()
            except Exception:
                logger.exception('Stopped at %s', wp_subscription)
                raise

        logger.info(
            'Took %s to finish, subscriptions handled so far: %s/%s',
            time.time() - start_t,
            self.subscriptions_handled_count,
            self.total_count,
        )
