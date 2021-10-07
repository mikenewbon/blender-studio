# noqa: D100
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
import paypalrestsdk

from looper.models import Subscription
from looper import admin_log

logger = logging.getLogger('cancel_ipn')
logger.setLevel(logging.DEBUG)


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

        with open('billing_agreement_ids_active.txt') as f:
            f.readline()
            for line in f.readlines():
                subscription_id = line.split()[0].strip()
                subscription = Subscription.objects.filter(pk=subscription_id).first()
                billing_agreement_id = line.split()[1].strip()
                logger.debug(
                    f'Subscription #{subscription_id} ({subscription}), '
                    f'billing agreement #{billing_agreement_id}'
                )
                billing_agreement = paypalrestsdk.BillingAgreement.find(
                    billing_agreement_id, api=self.api
                )
                if not billing_agreement or not billing_agreement.state:
                    continue

                if billing_agreement.state.lower() in ('active', 'suspended'):
                    self._cancel_billing_agreement(subscription, billing_agreement)

    def _log_action(self, message: str, subscription: Subscription):
        logger.warning(message)
        if not self.is_dry_run and subscription:
            admin_log.attach_log_entry(subscription, message)

    def _cancel_billing_agreement(self, subscription: Subscription, billing_agreement):
        message = f'Cancelled PayPal billing agreement {billing_agreement.id}'
        self._log_action(message, subscription)
        if self.is_dry_run:
            return

        # Cancel the agreement
        cancel_note = {
            'note': (
                'Cancelling the agreement: '
                'PayPal billing agreements are no longer supported by Blender Cloud. '
                'Visit https://cloud.blender.org/settings/billing/ to manage your subscription.'
            )
        }
        if billing_agreement.cancel(cancel_note):
            billing_agreement = paypalrestsdk.BillingAgreement.find(
                billing_agreement.id, api=self.api
            )
            logger.warning(
                "Billing Agreement [%s] has state %s"
                % (billing_agreement.id, billing_agreement.state),
            )
            # Would expect status has changed to Cancelled
            assert (
                billing_agreement.state.lower() == 'cancelled'
            ), f'Unexpected state of billing agreement: {billing_agreement.state}'
