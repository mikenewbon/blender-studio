import json
import logging
from typing import Type, Any, List

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from blog.models import Revision
from films.models import Film, Asset
from search.health_check import check_meilisearch
from search.queries import SearchableModel, get_searchable_queryset, set_thumbnail_and_url
from training.models import Training, Section

log = logging.getLogger(__name__)


def add_documents(data_to_load: List[Any]) -> None:
    """Add document to the main index and to replica indexes."""
    check_meilisearch(check_indexes=True)
    settings.MAIN_SEARCH_INDEX.add_documents(data_to_load)

    # There seems to be no way in MeiliSearch v0.13 to disable adding new document
    # fields automatically to searchable attrs, so we update the settings to set them:
    settings.MAIN_SEARCH_INDEX.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Revision)
def update_search_index(
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
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
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
) -> None:
    pass
    # TODO(Natalia): add post_delete signal to remove deleted objects from the search index
