from typing import Union

from django.db.models.signals import post_save
from django.dispatch import receiver

from films.models import Film, Asset
from training.models import Training


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
def update_search_index(sender: Union[Film, Asset, Training], instance, created, **kwargs) -> None:
    pass


# TODO(Natalia): add post_delete signal to remove deleted objects from the search index
