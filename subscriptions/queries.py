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
