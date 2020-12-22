import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from common import markdown
from films.models.assets import Asset, AssetComment, Like
from films.models.collections import Collection
from users.queries import create_action_from_like

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Asset)
def clean_asset_description(sender: object, instance: Asset, **kwargs: object) -> None:
    """Clean asset description."""
    instance.description = markdown.sanitize(instance.description)


@receiver(pre_save, sender=Collection)
def clean_collection_text(sender: object, instance: Collection, **kwargs: object) -> None:
    """Clean collection text."""
    instance.text = markdown.sanitize(instance.text)


@receiver(post_save, sender=AssetComment)
def notify_about_comment(
    sender: object, instance: AssetComment, created: bool, **kwargs: object
) -> None:
    """
    Generate notifications about comments under film assets.

    Because asset <-> comment relation uses a custom through model (AssetComment),
    film asset is not accessible in post_save of a Comment, only in post_save of the through model.
    """
    if not created:
        return

    instance.comment.create_action()


@receiver(post_save, sender=Like)
def notify_about_like(sender: object, instance: Like, created: bool, **kwargs: object) -> None:
    """Generate notifications about asset likes."""
    if not created:
        return

    target = instance.asset
    # Don't notify when one likes their own blog post
    asset_author = target.static_asset.author or target.static_asset.user
    if instance.user == asset_author:
        return

    create_action_from_like(actor=instance.user, target=target)
