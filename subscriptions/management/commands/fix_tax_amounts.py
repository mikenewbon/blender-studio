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
        if order.pk in self.orders_seen:
            return

        self.orders_to_update.append(order)
        self.orders_seen.add(order.pk)

    def _add_subscription(self, subscription):
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

        subscription = order.subscription
        taxable = self._get_taxable(subscription)
        assert (
            order.tax_type == taxable.tax_type.value
        ), f'Order #{order.pk} tax type changed from {order.tax_type} to {taxable.tax_type}'

        # Not sure what to do with reverse-charged yet FIXME
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
                f'{order.tax_rate} -> {taxable.tax_rate} ({order.price})'
            )
            # Not expecting tax rate changes for anything except Ireland
            assert order.tax_country == 'IE', f'{order.tax_country} != IE'
            order.tax_rate = taxable.tax_rate
            self._add_order(order)

        if taxable.tax != order.tax:
            logger.info(
                f'Order #{order.pk} tax will be updated: '
                f'{order.tax} -> {taxable.tax} ({order.price}, {order.tax_rate}%)'
            )
            order.tax = taxable.tax
            self._add_order(order)

    def _handle_subscription(self, subscription):
        old_taxable = subscription.taxable

        taxable = self._get_taxable(subscription)
        assert old_taxable.tax_type.value == taxable.tax_type.value, (
            f'Subs #{subscription.pk} tax type changed from '
            f'{old_taxable.tax_type} to {taxable.tax_type} '
            f'({subscription.tax_country})'
        )

        if old_taxable.tax_rate != taxable.tax_rate:
            logger.info(
                f'Subs #{subscription.pk} tax rate will be updated: '
                f'{old_taxable.tax_rate} -> {taxable.tax_rate} '
                f'({subscription.price})'
            )
            # Not expecting tax rate changes for anything except Ireland
            assert subscription.tax_country == 'IE', f'{subscription.tax_country} != IE'
            subscription.tax_rate = taxable.tax_rate
            self._add_subscription(subscription)

        if taxable.tax != subscription.tax:
            logger.info(
                f'Subs #{subscription.pk} tax will be updated: '
                f'{taxable.tax} -> {subscription.tax} '
                f'({subscription.price}, {subscription.tax_rate})'
            )
            subscription.tax = taxable.tax
            self._add_subscription(subscription)

    def handle(self, *args, **options):
        """Loop over recent subscriptions and their order to update their tax amounts."""
        orders_q = (
            Order.objects.select_related('subscription', 'user')
            .filter(
                created_at__gte='2021-07-01',
                tax_type=looper.taxes.TaxType.VAT_CHARGE.value,
                # tax_country='IE',
                # FIXME: handle reverse-charged ones later
                user__customer__vat_number='',
            )
            .exclude(
                # FIXME(anna): will most likely need to add exceptions
                # for GB and MC, because pyvat only tracks EU member
                # states
                tax_country__in=('GB', 'IE', 'MC'),
            )
            .exclude(
                subscription__tax_country__in=('GB', 'IE', 'MC'),
            )
            .exclude(
                tax_type=looper.taxes.TaxType.NO_CHARGE.value,
            )
        )
        logger.info('Total orders to fix: %s', orders_q.count())
        self.subscriptions_to_update = []
        self.orders_to_update = []
        self.subscriptions_seen = set()
        self.orders_seen = set()

        for order in orders_q:
            assert order.tax_country != 'GB'
            self._handle_order(order)
        logger.info('Orders to update: %s', len(self.orders_to_update))
        logger.info('Subscriptions to update: %s', len(self.subscriptions_to_update))

        return  # FIXME uncomment after reviewing all the changes and run again
        fields = {'tax', 'tax_rate'}
        if self.subscriptions_to_update:
            Subscription.objects.bulk_update(self.subscriptions_to_update, fields=fields)
        if self.orders_to_update:
            Order.objects.bulk_update(self.orders_to_update, fields=fields)
