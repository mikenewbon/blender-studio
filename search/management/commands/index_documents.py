from typing import List, Dict
from typing import Optional, Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from search.health_check import MeiliSearchServiceError, check_meilisearch
from search.serializers.main_search import MainSearchSerializer
from search.serializers.training_search import TrainingSearchSerializer
from search.serializers.base import BaseSearchSerializer


class Command(BaseCommand):
    help = (
        f'Add database objects to the main search index "{settings.MEILISEARCH_INDEX_UID}". '
        f'Also update replica indexes for different search results ordering. The following '
        f'models are indexed: Film, Asset, Training, Section, Post. '
        f'Objects already present in the indexes are updated.'
    )

    def _prepare_data(self, serializer: BaseSearchSerializer) -> Any:
        objects_to_load: List[Dict[str, Any]] = []

        for model in serializer.models_to_index:
            queryset = serializer.get_searchable_queryset(model)
            self.stdout.write(f'Preparing {len(queryset)} "{model._meta.label}" objects...')

            qs_values = serializer.prepare_data_for_indexing(queryset)
            objects_to_load.extend(qs_values)
            self.stdout.write(f'Done ({len(qs_values)} objects).')

        self.stdout.write(f'{len(objects_to_load)} objects to load')

        return objects_to_load

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        try:
            # Check the server and indexes first, before performing lengthy computations
            check_meilisearch(check_indexes=True)
        except MeiliSearchServiceError as err:
            raise CommandError(err)

        self.stdout.write('Preparing the data, it may take a while...')
        data_to_load = self._prepare_data(serializer=MainSearchSerializer())
        self.stdout.write('Preparing the training data, it may take a while...')
        training_data_to_load = self._prepare_data(serializer=TrainingSearchSerializer())

        # Update the main index, the replica indexes, and the training index
        indexes_to_update = [*settings.INDEXES_FOR_SORTING.keys(), settings.TRAINING_INDEX_UID]
        for index_uid in indexes_to_update:
            index = settings.SEARCH_CLIENT.get_index(index_uid)
            if index_uid == settings.TRAINING_INDEX_UID:
                response = index.add_documents(training_data_to_load)
                index.update_searchable_attributes(settings.TRAINING_SEARCHABLE_ATTRIBUTES)
            else:
                response = index.add_documents(data_to_load)
                # There seems to be no way in MeiliSearch v0.13 to disable adding new document
                # fields automatically to searchable attrs, so we update the settings to set them:
                index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated the index "{index_uid}". '
                    f'Update ID: {response["updateId"]}.'
                )
            )

        return str(response["updateId"])
