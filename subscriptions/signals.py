from datetime import timedelta
from typing import Set
import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.dispatch import receiver
import alphabetic_timestamp as ats
import django.db.models.signals as django_signals

from looper.models import Customer, Order
import looper.admin_log
import looper.signals

import subscriptions.models
import subscriptions.queries as queries
import subscriptions.tasks as tasks
import users.tasks

User = get_user_model()
logger = logging.getLogger(__name__)

subscription_created_needs_payment = django_signals.Signal(providing_args=[])


def timebased_order_number():
    """Generate a short sequential number for an order."""
    return ats.base36.now(time_unit=ats.TimeUnit.milliseconds).upper()


@receiver(django_signals.post_save, sender=User)
def create_customer(sender, instance: User, created, **kwargs):
    """Create Customer on User creation."""
    if not created:
        return
    logger.debug("Creating Customer for user %i" % instance.id)
    # Assume billing name and email are the same, they should be able to change them later
    Customer.objects.create(
        user_id=instance.pk,
        billing_email=instance.email,
        full_name=instance.full_name,
    )


@receiver(django_signals.pre_save, sender=Order)
def _set_order_number(sender, instance: Order, **kwargs):
    if instance.pk or instance.number or instance.is_legacy:
        return
    instance.number = timebased_order_number()
    assert instance.number


@receiver(subscription_created_needs_payment)
def _on_subscription_created_needs_payment(sender: looper.models.Subscription, **kwargs):
    tasks.send_mail_bank_transfer_required(subscription_id=sender.pk)
    users.tasks.grant_blender_id_role(pk=sender.user_id, role='cloud_has_subscription')


@receiver(looper.signals.subscription_activated)
@receiver(looper.signals.subscription_deactivated)
def _on_subscription_status_changed(sender: looper.models.Subscription, **kwargs):
    tasks.send_mail_subscription_status_changed(subscription_id=sender.pk)


@receiver(looper.signals.subscription_activated)
def _on_subscription_status_activated(sender: looper.models.Subscription, **kwargs):
    users.tasks.grant_blender_id_role(pk=sender.user_id, role='cloud_has_subscription')
    users.tasks.grant_blender_id_role(pk=sender.user_id, role='cloud_subscriber')

    if not hasattr(sender, 'team'):
        return
    # Also grant badges to team members
    for team_user in sender.team.users.all():
        users.tasks.grant_blender_id_role(pk=team_user.pk, role='cloud_subscriber')


@receiver(looper.signals.subscription_deactivated)
@receiver(looper.signals.subscription_expired)
def _on_subscription_status_deactivated(sender: looper.models.Subscription, **kwargs):
    # No other active subscription exists, subscriber badge can be revoked
    if not queries.has_active_subscription(sender.user):
        users.tasks.revoke_blender_id_role(pk=sender.user_id, role='cloud_subscriber')

    if not hasattr(sender, 'team'):
        return
    # Also remove team members' badges
    for team_user in sender.team.users.all():
        # Revoke the badge, unless they have another active subscription
        if queries.has_active_subscription(team_user):
            continue
        users.tasks.revoke_blender_id_role(pk=team_user.pk, role='cloud_subscriber')


@receiver(looper.signals.automatic_payment_succesful)
@receiver(looper.signals.automatic_payment_soft_failed)
@receiver(looper.signals.automatic_payment_failed)
def _on_automatic_payment_performed(
    sender: looper.models.Order,
    transaction: looper.models.Transaction,
    **kwargs,
):
    # FIXME(anna): looper.clock sends the signal before updating the order record,
    # which breaks async execution because the task might be quick enough
    # to retrieve the order while it still has the previous (now, incorrect) status.
    sender.save(update_fields={'collection_attempts', 'status', 'retry_after'})

    tasks.send_mail_automatic_payment_performed(order_id=sender.pk, transaction_id=transaction.pk)


@receiver(looper.signals.managed_subscription_notification)
def _on_managed_subscription_notification(sender: looper.models.Subscription, **kwargs):
    tasks.send_mail_managed_subscription_notification(subscription_id=sender.pk)


@receiver(looper.signals.subscription_expired)
def _on_subscription_expired(sender: looper.models.Subscription, **kwargs):
    assert sender.status == 'expired', f'Expected expired, got "{sender.status} (pk={sender.pk})"'

    # Only send a "subscription expired" email when there are no other active subscriptions
    if not queries.has_active_subscription(sender.user):
        tasks.send_mail_subscription_expired(subscription_id=sender.pk)


@receiver(looper.signals.automatic_payment_soft_failed_no_payment_method)
@receiver(looper.signals.automatic_payment_failed_no_payment_method)
def _on_automatic_collection_failed_no_payment_method(sender: looper.models.Order, **kwargs):
    tasks.send_mail_no_payment_method(order_id=sender.pk)


@receiver(django_signals.post_save, sender=User)
def add_to_teams(sender, instance: User, created, **kwargs):
    """Add newly created user to teams containing their email."""
    if not created:
        return
    email_domain = instance.email.lower().split('@')[-1]
    for team in subscriptions.models.Team.objects.filter(
        Q(emails__contains=[instance.email]) | Q(email_domain=email_domain)
    ):
        team.add(instance)


@receiver(django_signals.post_save, sender=subscriptions.models.Team)
def set_team_users(sender, instance: subscriptions.models.Team, **kwargs):
    """Set team users to users with emails matching team emails."""
    emails = instance.emails
    current_team_users = instance.users.all()
    current_team_users_ids = {_.pk for _ in current_team_users}
    # Remove all users that are neither on the emails list, nor have emails that match email domain
    for user in current_team_users:
        if (
            user.email.lower() in emails
            or instance.email_domain
            and instance.email_domain.lower() in user.email.lower()
        ):
            continue
        instance.remove(user)

    # Add all users that are either on the emails list, or have emails that match the email domain
    email_q = Q(email__in=emails)
    if instance.email_domain:
        email_q = email_q | Q(email__contains=f'@{instance.email_domain}')
    matching_users = User.objects.filter(email_q)
    for user in matching_users:
        if user.pk in current_team_users_ids:
            continue
        instance.add(user)


@receiver(django_signals.m2m_changed, sender=subscriptions.models.Team.users.through)
def _on_team_change_grant_revoke_subscriber_badges(
    sender, instance: subscriptions.models.Team, action: str, pk_set: Set[int], **kwargs
):
    if action not in ('post_add', 'post_remove'):
        return

    # If team subscription is active, add the subscriber badge to the newly added team member
    is_team_subscription_active = instance.subscription.is_active
    for user_id in pk_set:
        user = User.objects.get(pk=user_id)
        if action == 'post_add' and is_team_subscription_active:
            # The task must be delayed because OAuthUserInfo might not exist at the moment
            # when a newly registered User is added to the team because its email matches.
            users.tasks.grant_blender_id_role(
                pk=user.pk, role='cloud_subscriber', schedule=timedelta(minutes=2)
            )
        elif action == 'post_remove' and not queries.has_active_subscription(user):
            users.tasks.revoke_blender_id_role(pk=user.pk, role='cloud_subscriber')


@receiver(django_signals.post_save, sender=Order)
def _add_invoice_reference(sender, instance: Order, created, **kwargs):
    # Only set external reference if this is a new order
    if not created:
        return
    # Only set external reference if order doesn't have one
    if instance.external_reference:
        return
    subscription = instance.subscription
    if not hasattr(subscription, 'team'):
        return
    if not subscription.team.invoice_reference:
        return

    instance.external_reference = subscription.team.invoice_reference
    instance.save(update_fields={'external_reference'})
