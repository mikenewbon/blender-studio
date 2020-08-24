import logging
from abc import ABC
from typing import Type, Any, List

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from blog.models import Revision
from films.models import Film, Asset
from search.health_check import check_meilisearch, MeiliSearchServiceError
from search.serializers.base import SearchableModel, BaseSearchSerializer
from search.serializers.main_search import MainSearchSerializer
from search.serializers.training_search import TrainingSearchSerializer
from training.models import Training, Section

log = logging.getLogger(__name__)


class BasePostSaveSearchIndexer(ABC):
    """A base class for post_save signal handlers.

    Attributes:
        index_uids: A list of index uids to which a document should be added.
        serializer: A BaseSearchSerializer instance, used to prepare the object to be
            added to the indexes from the index_uids list.
    """

    index_uids: List[str]
    serializer: BaseSearchSerializer

    def _add_documents_to_index(self, data_to_load: List[Any]) -> None:
        try:
            check_meilisearch(check_indexes=True)
        except MeiliSearchServiceError as err:
            log.error(f'Did not update the {self.index_uids} search indexes post_save: {err}')
            return

        for index_uid in self.index_uids:
            index = settings.SEARCH_CLIENT.get_index(index_uid)
            index.add_documents(data_to_load)

            # There seems to be no way in MeiliSearch v0.13.0 to disable adding new document
            # fields automatically to searchable attrs, so we update the settings to set them:
            index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)

    def handle(self, sender: Type[SearchableModel], instance: SearchableModel) -> None:
        """Indexes the objects that should be available in search."""
        instance_qs = self.serializer.get_searchable_queryset(sender, id=instance.id)
        if instance_qs:
            data_to_load = self.serializer.prepare_data_for_indexing(instance_qs)
            self._add_documents_to_index(data_to_load)
            log.info(f'Added {instance} to the {self.index_uids} search indexes.')


class MainPostSaveSearchIndexer(BasePostSaveSearchIndexer):
    """Post_save signal handler, adds documents to the main index and its replicas."""

    index_uids = list(settings.INDEXES_FOR_SORTING.keys())
    serializer = MainSearchSerializer()


class TrainingPostSaveSearchIndexer(BasePostSaveSearchIndexer):
    """Post_save signal handler, adds documents to the training index."""

    index_uids = [settings.TRAINING_INDEX_UID]
    serializer = TrainingSearchSerializer()


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Revision)
def update_main_search_indexes(
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
) -> None:
    """Adds new objects to the main search indexes and updates the updated ones."""
    indexer = MainPostSaveSearchIndexer()
    indexer.handle(sender=sender, instance=instance)


@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Asset)
def update_training_search_index(
    sender: Type[SearchableModel], instance: SearchableModel, **kwargs: Any
) -> None:
    """Adds new objects to the training search index and updates the updated ones.

    For the training search, Trainings, Sections and production lessons (an Asset
    category) are indexed.
    """
    indexer = TrainingPostSaveSearchIndexer()
    indexer.handle(sender=sender, instance=instance)


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
        log.error(f'Did not update search indexes pre_delete: {err}')
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
