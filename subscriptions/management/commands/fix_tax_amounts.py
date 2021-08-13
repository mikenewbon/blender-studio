"""Updates tax amounts for subscriptions and orders after VAT calculations changed."""
import logging

from django.core.management.base import BaseCommand

from looper.models import Order, Subscription
import looper.taxes

logger = logging.getLogger('fix_tax')
logger.setLevel(logging.DEBUG)
admin_url = 'https://cloud.blender.org/admin/'


class Command(BaseCommand):
    """Go over latest orders with incorrect tax amounts and update them."""

    def _add_order(self, order):
        assert isinstance(order, Order)
        if order.pk in self.orders_seen:
            return

        self.orders_to_update.append(order)
        self.orders_seen.add(order.pk)

    def _add_subscription(self, subscription):
        assert isinstance(subscription, Subscription)
        if subscription.pk in self.subscriptions_seen:
            return

        self.subscriptions_to_update.append(subscription)
        self.subscriptions_seen.add(subscription.pk)

    def _get_taxable(self, subscription):
        """Calculate tax rate using tax country already set on the subscription."""
        tax_country = subscription.tax_country
        product_type = subscription.plan.product.type
        tax_type, tax_rate = looper.taxes.ProductType(product_type).get_tax(
            buyer_country_code=tax_country,
            is_business=False,
        )
        return looper.taxes.Taxable(subscription.price, tax_type=tax_type, tax_rate=tax_rate)

    def _handle_order(self, order):
        # Make sure subscription's tax rate is recalculated
        if order.subscription_id not in self.subscriptions_seen:
            self._handle_subscription(order.subscription)

        # Not sure what to do with reverse-charged yet FIXME

        subscription = order.subscription
        taxable = self._get_taxable(subscription)

        assert order.tax_type == taxable.tax_type.value, (
            f'Not expecting tax type changes for '
            f'{order.tax_country}: {order.tax_type} -> {taxable.tax_type}'
        )
        if order.tax_type != taxable.tax_type.value:
            assert order.tax_country == 'GB', (
                f'Not expecting tax type changes for '
                f'{order.tax_country}: {order.tax_type} -> {taxable.tax_type}'
            )
            logger.info(
                f'Order #{order.pk} tax type changed from {order.tax_type} to {taxable.tax_type}, '
                f'({order.tax_country})'
            )
            order.tax_type = taxable.tax_type.value
            self._add_order(order)

        if order.price != order.subscription.price:
            subs_url = f'{admin_url}looper/subscription/{order.subscription_id}/change/'
            logger.info(
                f'{subs_url}, skipping Order #{order.pk}: '
                f'{order.price} != {order.subscription.price}'
            )
            return
        if taxable.tax_rate != order.tax_rate:
            logger.info(
                f'Order #{order.pk} tax rate will be updated: '
                f'{order.tax_rate} -> {taxable.tax_rate} ({order.price}, {order.tax_country})'
            )
            # Not expecting tax rate changes for anything except Ireland
            expected = ('GB', 'IE')
            assert order.tax_country in expected, f'{order.tax_country} not {expected}'
            order.tax_rate = taxable.tax_rate
            self._add_order(order)

        if taxable.tax != order.tax:
            logger.info(
                f'Order #{order.pk} tax will be updated: '
                f'{order.tax} -> {taxable.tax} ({order.price}, '
                f'{order.tax_rate}%, {order.tax_country})'
            )
            order.tax = taxable.tax
            self._add_order(order)

    def _handle_subscription(self, subscription):
        taxable = self._get_taxable(subscription)

        # assert subscription.tax_type == taxable.tax_type.value, (
        #    f'Not expecting tax type changes for '
        #    f'{subscription.tax_country}: {subscription.tax_type} -> {taxable.tax_type}'
        # )
        if subscription.tax_type != taxable.tax_type.value:
            expected = ('EE',)
            logger.info(
                f'Subs #{subscription.pk} tax type changed from '
                f'{subscription.tax_type} to {taxable.tax_type} '
                f'({subscription.tax_country})'
            )
            assert subscription.tax_country in expected, (
                f'Not expecting tax type changes for '
                f'{subscription.tax_country}: {subscription.tax_type} -> {taxable.tax_type}'
            )
            subscription.tax_type = taxable.tax_type.value
            self._add_subscription(subscription)

        if subscription.tax_rate != taxable.tax_rate:
            logger.info(
                f'Subs #{subscription.pk} tax rate will be updated: '
                f'{subscription.tax_rate} -> {taxable.tax_rate} '
                f'({subscription.price}, {subscription.tax_country})'
            )
            # Not expecting tax rate changes for anything except Ireland
            expected = ('GB', 'IE', 'EE')
            # Add IDs here after reviewing the unexpected changes
            expected_ids = []
            assert (
                subscription.tax_country in expected or subscription.pk in expected_ids
            ), f'{subscription.tax_country} not {expected}'
            subscription.tax_rate = taxable.tax_rate
            self._add_subscription(subscription)

        if taxable.tax != subscription.tax:
            logger.info(
                f'Subs #{subscription.pk} tax will be updated: '
                f'{subscription.tax} -> {taxable.tax} '
                f'({subscription.price}, {subscription.tax_rate}, {subscription.tax_country})'
            )
            subscription.tax = taxable.tax
            self._add_subscription(subscription)

    def _find_orders(self):
        """Loop over recent orders to update their tax amounts."""
        orders_q = (
            Order.objects.select_related('subscription', 'user')
            .filter(
                created_at__gte='2021-07-01',
                tax_type=looper.taxes.TaxType.VAT_CHARGE.value,
                # FIXME: handle reverse-charged ones later
                user__customer__vat_number='',
            )
            .exclude(
                tax_type=looper.taxes.TaxType.NO_CHARGE.value,
            )
            .exclude(tax_country__in=('GB',))
        )
        logger.info('Total orders to fix: %s', orders_q.count())
        self.subscriptions_to_update = []
        self.orders_to_update = []
        self.subscriptions_seen = set()
        self.orders_seen = set()

        for order in orders_q:
            self._handle_order(order)
        logger.info('Orders to update: %s', len(self.orders_to_update))
        per_country_code = {}
        for _ in self.orders_to_update:
            per_country_code[_.tax_country] = per_country_code.get(_.tax_country, 0) + 1
        for _ in self.subscriptions_to_update:
            per_country_code[_.tax_country] = per_country_code.get(_.tax_country, 0) + 1
        logger.info(per_country_code)
        logger.info('Subscriptions to update: %s', len(self.subscriptions_to_update))

        return  # FIXME comment out after reviewing all the changes and run again
        fields = {'tax', 'tax_rate'}
        if self.subscriptions_to_update:
            Subscription.objects.bulk_update(self.subscriptions_to_update, fields=fields)
        if self.orders_to_update:
            Order.objects.bulk_update(self.orders_to_update, fields=fields)

    def _find_subscriptions(self):
        """Loop over subscriptions to update their tax amounts."""
        subscriptions_q = Subscription.objects.filter(
            tax_type=looper.taxes.TaxType.VAT_CHARGE.value,
            tax_country__in=('GB',),
            # FIXME: handle reverse-charged ones later
            user__customer__vat_number='',
        )
        logger.info('Total subscriptions to review: %s', subscriptions_q.count())
        self.subscriptions_to_update = []
        self.subscriptions_seen = set()

        for sub in subscriptions_q:
            self._handle_subscription(sub)
        logger.info('Subscriptions to update: %s', len(self.subscriptions_to_update))

        return  # FIXME comment out after reviewing all the changes and run again
        fields = {'tax', 'tax_rate'}
        if self.subscriptions_to_update:
            Subscription.objects.bulk_update(
                self.subscriptions_to_update, fields=fields, batch_size=500
            )

    def handle(self, *args, **options):
        """Find orders and/or subscriptions with incorrect tax amounts/rates and update them."""
        # self._find_orders()
        self._find_subscriptions()
