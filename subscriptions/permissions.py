# noqa: D100
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.db.models.query_utils import Q

from looper.models import Customer, Subscription

from subscriptions.models import Organization, Subscriber

User = get_user_model()


def can_change_customer(user: User, customer: Customer) -> bool:  # noqa: D103
    if not user.is_authenticated:
        return False

    try:
        subscriber: Subscriber = customer.subscriber
        return subscriber.user_id == user.id
    except Subscriber.DoesNotExist:
        pass

    try:
        organization: Organization = customer.organization
        return organization.organization_users.filter(
            can_change_organization=True, user_id=user.id
        ).exists()
    except Organization.DoesNotExist:
        pass

    return False


def has_subscription(user: User) -> bool:  # noqa: D103
    if not user.is_authenticated:
        return False

    active_subscriptions: 'QuerySet[Subscription]' = Subscription.objects.active()

    return active_subscriptions.filter(
        Q(customer__subscriber__user_id=user.id) | Q(customer__organization__users__id=user.id)
    ).exists()
