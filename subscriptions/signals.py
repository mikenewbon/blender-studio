import logging

from django.contrib.auth import get_user_model
from django.dispatch import receiver
import alphabetic_timestamp as ats
import django.db.models.signals as django_signals

from looper.models import Customer, Order
import looper.signals

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

    # TODO(anna): if this Subscription is a team subscription,
    # the task has to be called for user IDs of the team members
    users.tasks.grant_blender_id_role(pk=sender.user_id, role='cloud_has_subscription')


@receiver(looper.signals.subscription_activated)
@receiver(looper.signals.subscription_deactivated)
def _on_subscription_status_changed(sender: looper.models.Subscription, **kwargs):
    tasks.send_mail_subscription_status_changed(subscription_id=sender.pk)


@receiver(looper.signals.subscription_activated)
def _on_subscription_status_activated(sender: looper.models.Subscription, **kwargs):
    # TODO(anna): if this Subscription is a team subscription,
    # the task has to be called for user IDs of the team members
    users.tasks.grant_blender_id_role(pk=sender.user_id, role='cloud_has_subscription')
    users.tasks.grant_blender_id_role(pk=sender.user_id, role='cloud_subscriber')


@receiver(looper.signals.subscription_deactivated)
@receiver(looper.signals.subscription_expired)
def _on_subscription_status_deactivated(sender: looper.models.Subscription, **kwargs):
    # TODO(anna): if this Subscription is a team subscription,
    # the task has to be called for user IDs of the team members

    # No other active subscription exists, subscriber badge can be revoked
    if not queries.has_active_subscription(sender.user):
        users.tasks.revoke_blender_id_role(pk=sender.user_id, role='cloud_subscriber')


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
