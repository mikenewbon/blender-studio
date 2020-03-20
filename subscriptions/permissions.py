from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from django.http import HttpRequest
from looper.models import Customer, Subscription

from subscriptions.models import Organization, Subscriber


def can_change_customer(request: HttpRequest, customer: Customer) -> bool:
    if not request.user.is_authenticated:
        return False

    try:
        return customer.subscriber.user_id == request.user.id
    except Subscriber.DoesNotExist:
        pass

    try:
        return customer.organization.organization_users.filter(
            can_change_organization=True, user_id=request.user.id
        ).exists()
    except Organization.DoesNotExist:
        pass

    return False


def has_subscription(user: User) -> bool:
    if not user.is_authenticated:
        return False

    return (
        Subscription.objects.active()
        .filter(
            Q(customer__subscriber__user_id=user.id) | Q(customer__organization__users__id=user.id)
        )
        .exists()
    )
