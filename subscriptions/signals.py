import logging

from django.contrib.auth import get_user_model
from django.dispatch import receiver
import django.db.models.signals as django_signals

from looper.models import Customer

User = get_user_model()
logger = logging.getLogger(__name__)


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


# TODO(anna) looper:subscription_activated -> make has_active_subscription happen
# TODO(anna) looper.subscription_deactivated -> undo has_active_subscription
