from typing import Dict
import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from blender_id_oauth_client import signals as bid_signals

from profiles.models import Profile

logger = logging.getLogger(__name__)


@receiver(bid_signals.user_created)
def fill_profile(
    sender: object, instance: User, oauth_info: Dict[str, str], **kwargs: object
) -> None:
    """Update a Profile when a new OAuth user is created.

    Copy 'full_name' from the received 'oauth_info' and attempt to copy avatar from Blender ID.
    """
    if not hasattr(instance, 'profile'):
        logger.warning(f'User pk={instance.pk} is missing a profile')
        return

    instance.profile.full_name = oauth_info.get('full_name') or ''
    instance.profile.save()

    instance.profile.copy_avatar_from_blender_id()


@receiver(post_save, sender=User)
def create_profile(sender: object, instance: User, created: bool, **kwargs: object) -> None:
    """Create a Profile record for a newly created User."""
    if not created:
        return

    if not getattr(instance, 'profile', None):
        logger.info('Creating new Profile for user pk={instance.pk}')
        Profile.objects.create(user=instance)
