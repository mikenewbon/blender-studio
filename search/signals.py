import json
import logging
from typing import Type, Any, List, Optional

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from blog.models import Revision
from films.models import Film, Asset, AssetCategory
from search.health_check import check_meilisearch, MeiliSearchServiceError
from search.queries import SearchableModel, get_searchable_queryset, set_individual_fields
from training.models import Training, Section

log = logging.getLogger(__name__)


def prepare_data(instance: SearchableModel, instance_qs: 'QuerySet[SearchableModel]') -> List[Any]:
    """Serializes the instance and adds search-relevant data."""
    instance_dict = instance_qs.values().get()
    instance_dict = set_individual_fields(instance_dict, instance)
    # Data has to be a list of documents.
    return [json.loads(json.dumps(instance_dict, cls=DjangoJSONEncoder))]


def add_documents(data_to_load: List[Any], training: Optional[bool] = False) -> None:
    """Add document to the main index and its replica indexes, and optionally to training index."""
    try:
        check_meilisearch(check_indexes=True, check_training=training)
    except MeiliSearchServiceError as err:
        log.error('Did not update search index post_save.', exc_info=err)
        return

    indexes_to_update = [i[0] for i in settings.INDEXES_FOR_SORTING]
    if training:
        indexes_to_update.append(settings.TRAINING_INDEX_UID)

    for index_uid in indexes_to_update:
        index = settings.SEARCH_CLIENT.get_index(index_uid)
        index.add_documents(data_to_load)

        # There seems to be no way in MeiliSearch v0.13 to disable adding new document
        # fields automatically to searchable attrs, so we update the settings to set them:
        index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Revision)
def update_search_index(
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
) -> None:
    """Adds new objects to the search indexes and updates the updated ones.

    Trainings, sections and production lessons (an Asset category) are also added
    to the training-specific search index.
    """
    instance_qs = get_searchable_queryset(sender, id=instance.id)
    if instance_qs:
        data_to_load = prepare_data(instance, instance_qs)

        instance_is_relevant_to_training = isinstance(instance, (Training, Section)) or (
            isinstance(instance, Asset) and instance.category == AssetCategory.production_lesson
        )
        add_documents(data_to_load, training=instance_is_relevant_to_training)

        log.info(f'Added {instance} to the search index.')
        if instance_is_relevant_to_training:
            log.info(f'Added {instance} to the training search index.')


@receiver(pre_delete, sender=Film)
@receiver(pre_delete, sender=Asset)
@receiver(pre_delete, sender=Training)
@receiver(pre_delete, sender=Section)
@receiver(pre_delete, sender=Revision)
def delete_from_index(
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
) -> None:
    try:
        check_meilisearch(check_indexes=True)
    except MeiliSearchServiceError as err:
        log.error(f'Did not update search index pre_delete: {err}')
        return

    if isinstance(instance, Revision):
        # Only send the signal if the deleted revision is the latest one of a post.
        # Normally revisions should only be deleted when the related blog post is deleted.
        # TODO(Nat): Manually deleting a revision won't revert the indexed post version to the previous one.
        if (
            instance.post.is_published
            and instance.post.revisions.filter(is_published=True).latest('date_created').pk
            == instance.pk
        ):
            search_id = f'post_{instance.post.id}'
        else:
            return
    else:
        search_id = f'{sender._meta.model_name}_{instance.id}'

    for index_uid, _ in settings.INDEXES_FOR_SORTING:
        settings.SEARCH_CLIENT.get_index(index_uid).delete_document(search_id)
