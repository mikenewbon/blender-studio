# noqa: D100
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
import dateutil.parser
import paypalrestsdk

from looper.models import Subscription

from common import mailgun
from emails.models import Email
from emails.util import get_template_context
from subscriptions.tasks import _construct_subscription_mail

logger = logging.getLogger('mail_ipn')
logger.setLevel(logging.DEBUG)


def _get_or_create_email(subscription: Subscription, **extra_context) -> Email:
    user = subscription.user
    customer = user.customer
    email = customer.billing_email or user.email

    # An Unsubscribe record will prevent this message from being delivered by Mailgun.
    # This records might have been previously created for an existing account.
    mailgun.delete_unsubscribe_record(email)

    context = {
        'user': subscription.user,
        'email': email,
        'subscription': subscription,
        **get_template_context(),
        **extra_context,
    }

    mail_name = 'paypal_subscription_cancelled'
    email_body_html, email_body_txt, subject = _construct_subscription_mail(mail_name, context)

    email_obj, is_new = Email.objects.get_or_create(
        subject=subject,
        to=email,
        from_email=settings.DEFAULT_FROM_EMAIL,
        reply_to=settings.ADMIN_MAIL,
    )
    if is_new:
        logger.debug('Created an email to %s', email)
    else:
        logger.debug('Found an existing "%s" email to %s', email_obj, email)
    email_obj.base_html_template = ''
    email_obj.message = email_body_txt
    email_obj.html_message = email_body_html
    email_obj.save()
    return email


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
                if not subscription or subscription.is_cancelled:
                    continue
                if subscription.payment_method:
                    continue

                last_payment_date = dateutil.parser.parse(
                    billing_agreement.agreement_details.last_payment_date
                )
                if self.is_dry_run:
                    logger.warning(
                        'Would create an email for subscription %s (status %s)',
                        subscription.pk,
                        subscription.status,
                    )
                    continue

                _get_or_create_email(
                    subscription,
                    billing_agreement_id=billing_agreement.id,
                    billing_agreement_last_payment_date=last_payment_date,
                )
