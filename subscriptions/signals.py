import logging

from django.contrib.auth import get_user_model
from django.dispatch import receiver
import alphabetic_timestamp as ats
import django.db.models.signals as django_signals

from looper.models import Customer, Order
import looper.signals

import subscriptions.tasks as tasks

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


@receiver(looper.signals.subscription_activated)
@receiver(looper.signals.subscription_deactivated)
def _on_subscription_status_changed(sender: looper.models.Subscription, **kwargs):
    tasks.send_mail_subscription_status_changed(subscription_id=sender.pk)


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
