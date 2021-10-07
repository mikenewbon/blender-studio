# noqa: D100
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
import dateutil.parser
import paypalrestsdk

from looper.models import Subscription, Order
from looper import admin_log

from emails.util import _get_site_url

logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
start_date = "2021-06-01"
end_date = "2021-09-30"


def _turn_off_auto_now(ModelClass, field_name):
    def auto_now_off(field):
        field.auto_now = False

    _modify_model_field(ModelClass, field_name, auto_now_off)


def _turn_off_auto_now_add(ModelClass, field_name):
    def auto_now_add_off(field):
        field.auto_now_add = False

    _modify_model_field(ModelClass, field_name, auto_now_add_off)


def _modify_model_field(ModelClass, field_name, func):
    field = ModelClass._meta.get_field(field_name)
    func(field)


_turn_off_auto_now_add(Order, 'created_at')
_turn_off_auto_now(Order, 'updated_at')


def _write_row(f, *values):
    line = ';'.join(f'"{_}"' for _ in values) + '\n'
    f.write(line)


def _write_to_csv(f, data):
    admin_url = reverse('admin:looper_subscription_change', args=(data['subscription_id'],))
    values = (
        data['subscription_id'],
        data['subscription_status'],
        data['subscription_payment_method'],
        data['billing_agreement_id'],
        data['billing_agreement_state'],
        data.get('billing_agreement_last_payment_date', ''),
        data.get('billing_agreement_next_billing_date', ''),
        data.get('billing_agreement_payer_email', ''),
        data.get('email', ''),
        data.get('billing_email', ''),
        _get_site_url() + admin_url,
    )

    _write_row(f, *values)


class Command(BaseCommand):  # noqa: D101
    @property
    def is_dry_run(self) -> bool:
        """Return True if command was called with in dry run mode."""
        return self.options['dry_run']

    def add_arguments(self, parser):
        """Add custom arguments to the command."""
        parser.add_argument('--dry-run', dest='dry_run', action='store_true')
        parser.add_argument('--no-dry-run', dest='dry_run', action='store_false')
        parser.set_defaults(dry_run=True)

    def handle(self, *args, **options):  # noqa: D102
        self.options = options
        logger.warning('Dry run: %s', self.is_dry_run)
        self.api = paypalrestsdk.Api(
            {
                'mode': 'live',
                'client_id': settings.PAYPAL_CLIENT_ID,
                'client_secret': settings.PAYPAL_SECRET,
            }
        )
        self.sub_to_agreement = {}
        self.orders_to_upsert = []

        with open('billing_agreement_ids_active.txt') as f, open(
            'billing_agreements.csv', 'w+'
        ) as out_f:
            f.readline()
            _header = (
                'Subscription ID',
                'Subscription status',
                'Subscription payment method',
                'Agreement ID',
                'Agreement state',
                'Agreement last payment',
                'Agreement next payment',
                'Payer email',
                'BID email',
                'Billing email',
            )
            _write_row(out_f, *_header)

            for line in f.readlines():
                subscription_id = line.split()[0].strip()
                subscription = Subscription.objects.filter(pk=subscription_id).first()
                billing_agreement_id = line.split()[1].strip()
                self.sub_to_agreement[subscription_id] = {
                    'subscription_id': subscription_id,
                    'subscription_status': subscription.status if subscription else '',
                    'subscription_payment_method': str(subscription.payment_method)
                    if subscription
                    else '',
                    'billing_agreement_id': billing_agreement_id,
                    'billing_agreement': {},
                }
                data = self.sub_to_agreement[subscription_id]
                logger.debug(
                    f'Subscription #{subscription_id} ({subscription}), '
                    f'billing agreement #{billing_agreement_id}'
                )
                billing_agreement = paypalrestsdk.BillingAgreement.find(
                    billing_agreement_id, api=self.api
                )
                if not billing_agreement or not billing_agreement.state:
                    continue

                data[
                    'billing_agreement_last_payment_date'
                ] = billing_agreement.agreement_details.last_payment_date
                data[
                    'billing_agreement_next_billing_date'
                ] = billing_agreement.agreement_details.next_billing_date
                if subscription:
                    data['email'] = subscription.user.email
                    data['billing_email'] = subscription.user.customer.billing_email
                if billing_agreement.payer and billing_agreement.payer.payer_info:
                    data['billing_agreement_payer_email'] = billing_agreement.payer.payer_info.email

                if billing_agreement.state:
                    state = billing_agreement.state.lower()
                    data['billing_agreement_state'] = state

                    self._get_order_to_upsert(subscription, billing_agreement)
                    self._sync_next_payment(subscription, billing_agreement)

                _write_to_csv(out_f, data)
        self._upsert_orders()

    def _log_action(self, message: str, subscription: Subscription):
        logger.warning(message)
        if not self.is_dry_run and subscription:
            admin_log.attach_log_entry(subscription, message)

    def _upsert_orders(self):
        logger.info('Orders to upsert: %s', len(self.orders_to_upsert))
        if self.is_dry_run:
            return
        logger.info('Upserting %s orders', len(self.orders_to_upsert))
        Order.objects.bulk_create(sorted(self.orders_to_upsert, key=lambda x: x.created_at))

    def _order_from_transaction(self, subscription: Subscription, transaction) -> Order:
        if not subscription:
            return
        # assert transaction.status.lower() == 'completed', (
        #    f'Unexpected transaction status: {transaction.status}'
        # )
        if transaction.status.lower() != 'completed':
            return
        date_created = dateutil.parser.parse(transaction.time_stamp)
        existing_order = subscription.order_set.filter(created_at__date=date_created.date()).first()
        logger.debug(transaction)
        if not existing_order:
            order = subscription.generate_order(save=False)
            order.number = transaction.transaction_id
            order.created_at = date_created
            order.updated_at = date_created
            order.paid_at = date_created
            # not setting is_legacy flag because these orders are not in Blender Store
            # order.is_legacy = True
            generated_price = order.price
            order.price = int(float(transaction.amount.value) * 100)
            if generated_price != order.price:
                logger.error(
                    f'{subscription}, {transaction.transaction_id}: '
                    f'generated price {generated_price} != {order.price}'
                )
            order.status = 'paid'
            return order

    def _sync_next_payment(self, subscription, billing_agreement):
        if not subscription:
            return
        # If subscription already has a payment method, it shouldn't change
        if subscription.payment_method:
            return
        if not billing_agreement.agreement_details.next_billing_date:
            return

        next_payment_date = dateutil.parser.parse(
            billing_agreement.agreement_details.next_billing_date
        )
        old_next_payment_date = subscription.next_payment
        # Only update the date if it's singnificantly later than current next payment
        if (
            old_next_payment_date.date() == next_payment_date.date()
            or old_next_payment_date > next_payment_date
        ):
            return

        subscription.next_payment = next_payment_date
        msg = (
            f'Subscription #{subscription.pk} next payment date changed from'
            f' {old_next_payment_date} to {subscription.next_payment}'
            f' based on PayPal Billing Agreement {billing_agreement.id}'
        )
        self._log_action(msg, subscription)
        if not self.is_dry_run:
            Subscription.objects.bulk_update([subscription], fields={'next_payment'})

    def _get_order_to_upsert(self, subscription: Subscription, billing_agreement):
        logger.debug(billing_agreement)
        transactions = billing_agreement.search_transactions(start_date, end_date, api=self.api)
        orders = []
        for transaction in transactions.agreement_transaction_list:
            order = self._order_from_transaction(subscription, transaction)
            if order:
                msg = (
                    f'Adding order {order.number} to record a PayPal Billing Agreement transaction'
                )
                self._log_action(msg, subscription)
                orders.append(order)
        self.orders_to_upsert.extend(orders)
