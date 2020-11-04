import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

from films.models.assets import Asset
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
