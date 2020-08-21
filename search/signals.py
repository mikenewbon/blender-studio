import logging
from typing import Type, Any, List

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from blog.models import Revision
from films.models import Film, Asset
from search.health_check import check_meilisearch, MeiliSearchServiceError
from search.queries import MainSearchParser
from search.queries_training import TrainingSearchParser, SearchableModel
from training.models import Training, Section

log = logging.getLogger(__name__)


def add_documents_to_indexes(data_to_load: List[Any]) -> None:
    """Add documents to the main index and its replica indexes."""
    try:
        check_meilisearch(check_indexes=True)
    except MeiliSearchServiceError as err:
        log.error(f'Did not update search index post_save: {err}')
        return

    for index_uid in settings.INDEXES_FOR_SORTING.keys():
        index = settings.SEARCH_CLIENT.get_index(index_uid)
        index.add_documents(data_to_load)

        # There seems to be no way in MeiliSearch v0.13 to disable adding new document
        # fields automatically to searchable attrs, so we update the settings to set them:
        index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)


def add_documents_to_training_index(data_to_load: List[Any]) -> None:
    """Add documents to the training search index."""
    try:
        check_meilisearch(check_indexes=True)
    except MeiliSearchServiceError as err:
        log.error(f'Did not update search index post_save: {err}')
        return

    index = settings.SEARCH_CLIENT.get_index(settings.TRAINING_INDEX_UID)
    index.add_documents(data_to_load)

    # There seems to be no way in MeiliSearch v0.13 to disable adding new document
    # fields automatically to searchable attrs, so we update the settings to set them:
    index.update_searchable_attributes(settings.TRAINING_SEARCHABLE_ATTRIBUTES)


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Revision)
def update_search_index(
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
) -> None:
    """Adds new objects to the search indexes and updates the updated ones."""
    parser = MainSearchParser()
    instance_qs = parser.get_searchable_queryset(sender, id=instance.id)
    if instance_qs:
        data_to_load = parser.prepare_data_for_indexing(instance_qs)
        add_documents_to_indexes(data_to_load)
        log.info(f'Added {instance} to the search index.')


@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Asset)
def update_training_search_index(sender, instance, **kwargs):
    """Adds new objects to the training search index and updates the updated ones.

    Trainings, sections and production lessons (an Asset category) are indexed.
    """
    parser = TrainingSearchParser()
    instance_qs = parser.get_searchable_queryset(sender, id=instance.id)
    if instance_qs:
        data_to_load = parser.prepare_data_for_indexing(instance_qs)
        add_documents_to_training_index(data_to_load)
        log.info(f'Added {instance} to the training search index.')


@receiver(pre_delete, sender=Film)
@receiver(pre_delete, sender=Asset)
@receiver(pre_delete, sender=Training)
@receiver(pre_delete, sender=Section)
@receiver(pre_delete, sender=Revision)
def delete_from_index(
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
) -> None:
    """On object deletion, send a request to remove the related document from all indexes.

    If there is no related document in an index, nothing happens.
    """
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

    for index_uid in settings.ALL_INDEXES_UIDS:
        settings.SEARCH_CLIENT.get_index(index_uid).delete_document(search_id)
