from django.contrib.auth import get_user_model
from django.db.models import signals
import factory

from common.tests.factories.subscriptions import create_customer_with_billing_address
from common.tests.factories.users import UserFactory

User = get_user_model()


def _write_mail(mail, index=0):
    email = mail.outbox[index]
    name = email.subject.replace(' ', '_')
    with open(f'/tmp/{name}.txt', 'w+') as f:
        f.write(str(email.body))
    for content, mimetype in email.alternatives:
        with open(f'/tmp/{name}.{mimetype.replace("/", ".")}', 'w+') as f:
            f.write(str(content))


class _CreateCustomerAndBillingAddressMixin:
    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def setUp(self):
        # Create the admin user used for logging
        self.admin_user = UserFactory(
            id=1, email='admin@blender.studio', is_staff=True, is_superuser=True
        )
        # Reset ID sequence to avoid clashing with an already used ID 1
        UserFactory.reset_sequence(100, force=True)

        self.user = create_customer_with_billing_address(
            full_name='Алексей Н.',
            company='Testcompany B.V.',
            street_address='Billing street 1',
            extended_address='Floor 1',
            locality='Amsterdam',
            postal_code='1000AA',
            region='North Holland',
            country='NL',
            vat_number='NL-KVK-41202535',
            billing_email='billing@example.com',
        )
        self.customer = self.user.customer
        self.billing_address = self.customer.billing_address
