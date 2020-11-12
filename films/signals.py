import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from films.models.assets import Asset, AssetComment
from films.models.collections import Collection
from common import markdown

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
