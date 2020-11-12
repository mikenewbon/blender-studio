from typing import Dict
import logging

from actstream.models import Action
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from blender_id_oauth_client import signals as bid_signals

from profiles.models import Profile, Notification
from profiles.queries import set_groups

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

    group_names = oauth_info.get('roles') or []
    set_groups(instance, group_names=group_names)


@receiver(post_save, sender=User)
def create_profile(sender: object, instance: User, created: bool, **kwargs: object) -> None:
    """Create a Profile record for a newly created User."""
    if not created:
        return

    if not getattr(instance, 'profile', None):
        logger.info(f'Creating new Profile for user pk={instance.pk}')
        Profile.objects.create(user=instance)


@receiver(post_save, sender=Action)
def create_notification(sender: object, instance: Action, created: bool, **kwargs: object) -> None:
    """Create a Notification record to simplify retrieval of actions relevant to a user.

    Personal notifications include the following:
    * "someone commented on your blog post";
    * "someone liked your comment";
    * "someone replied to your comment";
    * TODO(anna): "someone saved your training section";
    * "someone commented on your training section";
    * "someone commented on your film asset";
    """
    if not created:
        return

    # There can be multiple users to whom this action is relevant
    users = set()
    action_object = instance.action_object
    verb = instance.verb
    target = instance.target

    # Notify about replies and comments likes
    if (
        action_object
        and getattr(action_object, 'user', None)
        and verb in [Action.objects.verb_replied, Action.objects.verb_liked]
    ):
        users.add(action_object.user)

    # Notify about comments on
    if target and verb in [Action.objects.verb_commented]:
        # blog `Post`s
        if getattr(target, 'author', None):
            users.add(target.author)
        # training `Section`s
        elif getattr(target, 'user', None):
            users.add(target.user)
        # film `Asset`s
        elif getattr(target, 'static_asset', None):
            asset_author = target.static_asset.author or target.static_asset.user
            if asset_author:
                users.add(asset_author)

    if not users:
        logger.debug(f'Unable to determine a relevant user for a new action: {instance}')
        return

    for user in users:
        # Don't notify yourself about your own actions: they can be viewed in activity
        if user == instance.actor:
            continue
        notification = Notification(user=user, action=instance)
        notification.save()
