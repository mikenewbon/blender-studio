"""Updates tax amounts for subscriptions and orders after VAT calculations changed."""
import logging

from django.core.management.base import BaseCommand

from looper.models import Subscription, PlanVariation
import looper.taxes
import looper.money

logger = logging.getLogger('fix_tax')
logger.setLevel(logging.DEBUG)
admin_url = 'https://cloud.blender.org/admin/'


class Command(BaseCommand):
    """Go over latest orders with incorrect tax amounts and update them."""

    def _add_subscription(self, subscription):
        assert isinstance(subscription, Subscription)
        if subscription.pk in self.subscriptions_seen:
            return

        self.subscriptions_to_update.append(subscription)
        self.subscriptions_seen.add(subscription.pk)

    def _get_taxable(self, subscription, is_business=False):
        """Calculate tax rate using tax country already set on the subscription."""
        tax_country = subscription.tax_country
        product_type = subscription.plan.product.type
        tax_type, tax_rate = looper.taxes.ProductType(product_type).get_tax(
            buyer_country_code=tax_country,
            is_business=is_business,
        )
        return looper.taxes.Taxable(subscription.price, tax_type=tax_type, tax_rate=tax_rate)

    def _handle_subscription(self, subscription):
        # This should only apply to legacy subscriptions
        assert subscription.is_legacy, f'Not a legacy subscription #{subscription.pk}!'
        taxable = self._get_taxable(subscription, is_business=True)
        original_pv = PlanVariation.objects.get(
            collection_method=subscription.collection_method,
            currency=subscription.currency,
            interval_unit=subscription.interval_unit,
            interval_length=subscription.interval_length,
        )
        original_full_price = original_pv.price
        deducted_price = subscription.price
        full_price = subscription.price + looper.money.Money(
            subscription.currency,
            round(subscription.price._cents * taxable.tax_rate / 100),
        )
        if abs(full_price._cents - original_full_price._cents) > 1:
            # This is an "irregular" scenario when subscription price
            # no longer matches its closest plan variation
            if subscription.price != full_price:
                logger.warning(
                    'Sub #%s (%s%% %s): price changes %s -> %s',
                    subscription.pk,
                    taxable.tax_rate,
                    subscription.tax_country,
                    subscription.price,
                    full_price,
                )
                subscription.price = full_price
                self._add_subscription(subscription)
        else:
            # This is a regular scenario when subscription price
            # matches a plan variation's, and we only need to update
            # the rate and copy that price, making sure that tax is
            # still 0 and order price does not change.
            if subscription.price != original_full_price:
                logger.warning(
                    'Sub #%s (%s%% %s): price changes %s -> %s',
                    subscription.pk,
                    taxable.tax_rate,
                    subscription.tax_country,
                    subscription.price,
                    original_full_price,
                )
                subscription.price = original_full_price
                self._add_subscription(subscription)

        if subscription.tax_rate != taxable.tax_rate:
            logger.warning(
                'Sub #%s (%s%% %s): tax rate changes %s -> %s',
                subscription.pk,
                taxable.tax_rate,
                subscription.tax_country,
                subscription.tax_rate,
                taxable.tax_rate,
            )
            subscription.tax_rate = taxable.tax_rate
            self._add_subscription(subscription)

        # some sanity checks that should apply to both scenarios
        taxable = subscription.taxable
        assert (
            taxable.price._cents == deducted_price._cents
        ), 'Sub #%s (%s%% %s): order price does not match changes %s -> %s' % (
            subscription.pk,
            taxable.tax_rate,
            subscription.tax_country,
            deducted_price,
            taxable.price,
        )
        test_order = subscription.generate_order(save=False)
        assert test_order.pk is None
        assert (
            test_order.price == deducted_price
        ), 'Sub #%s (%s%% %s): generated order price does not match changes %s -> %s' % (
            subscription.pk,
            taxable.tax_rate,
            subscription.tax_country,
            deducted_price,
            test_order.price,
        )
        assert (
            subscription.tax == taxable.charged_tax == looper.money.Money(subscription.currency, 0)
        ), 'Sub #%s (%s%% %s): tax changes %s -> %s' % (
            subscription.pk,
            taxable.tax_rate,
            subscription.tax_country,
            subscription.tax,
            taxable.charged_tax,
        )
        logger.info(
            'Sub #%s (%s%% %s): order price %s -> %s, tax %s [OK]',
            subscription.pk,
            taxable.tax_rate,
            subscription.tax_country,
            deducted_price,
            test_order.price,
            test_order.tax,
        )

    def _find_subscriptions(self):
        """Loop over subscriptions to update their tax amounts."""
        subscriptions_q = Subscription.objects.filter(
            tax_type=looper.taxes.TaxType.VAT_REVERSE_CHARGE.value,
            tax_rate=0,
            # tax_country='GB',
        )
        logger.info('Total subscriptions to review: %s', subscriptions_q.count())
        self.subscriptions_to_update = []
        self.subscriptions_seen = set()

        for sub in subscriptions_q:
            self._handle_subscription(sub)
        logger.info('Subscriptions to update: %s', len(self.subscriptions_to_update))

        return  # FIXME comment out after reviewing all the changes and run again
        fields = {'tax_rate', 'price'}
        if self.subscriptions_to_update:
            Subscription.objects.bulk_update(
                self.subscriptions_to_update, fields=fields, batch_size=500
            )

    def handle(self, *args, **options):
        """Find subscriptions with incorrect tax amounts/rates and update them."""
        self._find_subscriptions()
