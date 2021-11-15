# noqa: D100
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.db.models.query_utils import Q

from looper.models import Subscription

User = get_user_model()


def has_active_subscription(user: User) -> bool:
    """Check if a given user has an active subscription.

    Checks both for personal and team subscriptions.
    """
    if not user.is_authenticated:
        return False

    active_subscriptions: 'QuerySet[Subscription]' = Subscription.objects.active()

    return active_subscriptions.filter(
        Q(user_id=user.id) | Q(team__team_users__user_id=user.id)
    ).exists()


def has_non_legacy_subscription(user: User) -> bool:
    """Check if a given user has a subscription, ignoring legacy subscriptions.

    Checks both for personal and team subscriptions.
    """
    if not user.is_authenticated:
        return False

    subscriptions: 'QuerySet[Subscription]' = Subscription.objects.filter(is_legacy=False)

    return subscriptions.filter(Q(user_id=user.id) | Q(team__team_users__user_id=user.id)).exists()


def has_subscription(user: User) -> bool:
    """Check if a given user has any kind of subscription."""
    if not user.is_authenticated:
        return False

    return Subscription.objects.filter(
        Q(user_id=user.id) | Q(team__team_users__user_id=user.id)
    ).exists()


def should_redirect_to_billing(user: User) -> bool:
    """Figure out if checkout should redirect a given user to their billing."""
    if not user.is_authenticated:
        return False

    if user.subscription_set.exclude(status__in=Subscription._CANCELLED_STATUSES).count() == 0:
        # Only cancelled subscriptions, no need to redirect to billing
        return False

    return has_subscription(user) and any(
        # FIXME(anna): checkout creates an on-hold subscription with an order
        # so this seems to be the only currently available way to tell
        # when to stop showing the checkout to the customer.
        subscription.latest_order() and subscription.payment_method
        for subscription in user.subscription_set.all()
    )


def has_not_yet_cancelled_subscription(user: User) -> bool:
    """Check if a given user has any subscriptions that had not been cancelled yet.

    Checks only "personal", not team, subscriptions.
    """
    if not user.is_authenticated:
        return False

    not_yet_cancelled_subscriptions: 'QuerySet[Subscription]' = Subscription.objects.exclude(
        status__in=Subscription._CANCELLED_STATUSES
    )

    return not_yet_cancelled_subscriptions.filter(Q(user_id=user.id)).exists()
