import json
import logging
from typing import Type, Any, List

import meilisearch
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from blog.models import Revision
from films.models import Film, Asset
from search.queries import SearchableModels, get_searchable_queryset, set_thumbnail_and_url
from training.models import Training, Section

log = logging.getLogger(__name__)


def add_documents(data_to_load: List[Any]) -> None:
    """Add document to the main index and to replica indexes."""
    client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
    index = client.get_index(settings.MEILISEARCH_INDEX_UID)

    # TODO(Natalia): handle and log server errors
    index.add_documents(data_to_load)

    # There seems to be no way in MeiliSearch v0.13 to disable adding new document
    # fields automatically to searchable attrs, so we update the settings to set them:
    index.update_settings({'searchableAttributes': settings.SEARCHABLE_ATTRIBUTES})


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Revision)
def update_search_index(
    sender: Type[SearchableModels], instance: SearchableModels, **kwargs: Any
) -> None:
    """Adds new objects to the search index and updates the updated ones."""
    instance_qs = get_searchable_queryset(sender, id=instance.id)
    if instance_qs:
        instance_dict = instance_qs.values().get()
        instance_dict = set_thumbnail_and_url(instance_dict, instance)

        # Data has to be a list of documents.
        data_to_load = [json.loads(json.dumps(instance_dict, cls=DjangoJSONEncoder))]

        add_documents(data_to_load)
        log.info(f'Added {instance} to the search index.')


@receiver(post_delete, sender=Film)
@receiver(post_delete, sender=Asset)
@receiver(post_delete, sender=Training)
@receiver(post_delete, sender=Section)
@receiver(post_delete, sender=Revision)
def delete_from_index(
    sender: Type[SearchableModels], instance: SearchableModels, **kwargs: Any
) -> None:
    pass
    # TODO(Natalia): add post_delete signal to remove deleted objects from the search index
