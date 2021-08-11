from django.contrib.auth import get_user_model
from django.db.models import signals

from factory.django import DjangoModelFactory
import factory

import looper.models

from common.tests.factories.users import UserFactory
from subscriptions.models import Team

User = get_user_model()


class PaymentMethodFactory(DjangoModelFactory):
    class Meta:
        model = looper.models.PaymentMethod

    gateway_id = factory.LazyAttribute(lambda _: looper.models.Gateway.objects.first().pk)

    user = factory.SubFactory('common.tests.factories.users.UserFactory')


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = looper.models.Subscription

    plan_id = factory.LazyAttribute(lambda _: looper.models.Plan.objects.first().pk)
    payment_method = factory.SubFactory(PaymentMethodFactory)

    user = factory.SubFactory('common.tests.factories.users.UserFactory')


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = looper.models.Order

    user = factory.SubFactory('common.tests.factories.users.UserFactory')
    subscription = factory.SubFactory(SubscriptionFactory)
    payment_method = factory.SubFactory(PaymentMethodFactory)


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = looper.models.Transaction

    user = factory.SubFactory('common.tests.factories.users.UserFactory')
    order = factory.SubFactory(OrderFactory)
    payment_method = factory.SubFactory(PaymentMethodFactory)


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Faker('text', max_nb_chars=15)
    subscription = factory.SubFactory(SubscriptionFactory)


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = looper.models.Customer

    billing_email = factory.LazyAttribute(lambda o: '%s.billing@example.com' % o.user.username)
    user = factory.SubFactory('common.tests.factories.users.UserFactory')


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class AddressFactory(DjangoModelFactory):
    class Meta:
        model = looper.models.Address

    user = factory.SubFactory('common.tests.factories.users.UserFactory')


# TODO(anna): this should probably move to looper
@factory.django.mute_signals(signals.pre_save, signals.post_save)
def create_customer_with_billing_address(**data):
    """Use factories to create a User with a Customer and Address records."""
    customer_field_names = {f.name for f in looper.models.Customer._meta.get_fields()}
    address_field_names = {f.name for f in looper.models.Address._meta.get_fields()}
    user_field_names = {f.name for f in User._meta.get_fields()}

    address_kwargs = {k: v for k, v in data.items() if k in address_field_names}
    customer_kwargs = {k: v for k, v in data.items() if k in customer_field_names}
    user_kwargs = {k: v for k, v in data.items() if k in user_field_names}

    user = UserFactory(**user_kwargs)
    AddressFactory(user=user, **address_kwargs)
    CustomerFactory(user=user, **customer_kwargs)
    return user
