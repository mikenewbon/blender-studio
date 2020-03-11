from typing import Type

import django.db.models.signals as django_signals
import looper.models
from django.dispatch import receiver

from subscriptions.models import MembershipLevel, Membership


@receiver(django_signals.post_save, sender=looper.models.Subscription)
def create_membership_for_subscription(
    sender: Type[looper.models.Subscription],
    instance: looper.models.Subscription,
    created: bool,
    **kwargs: object,
) -> None:
    if not created:
        return None

    subscription = instance
    Membership.objects.create(
        user=subscription.user,
        subscription=subscription,
        level=MembershipLevel.objects.get(plan=subscription.plan),
    )
