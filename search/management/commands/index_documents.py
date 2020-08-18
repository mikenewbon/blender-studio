import json
from typing import List, Type, Union
from typing import Optional, Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import Model
from django.db.models.expressions import F, Value
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from taggit.models import Tag

from blog.models import Revision
from films.models import Film, Asset, AssetCategory
from search.health_check import MeiliSearchServiceError, check_meilisearch
from search.queries import set_individual_fields, get_searchable_queryset, SearchableModel
from search.queries_training import (
    get_searchable_queryset_for_training,
    set_individual_fields_for_training,
)
from training.models import Training, Section, TrainingStatus, TrainingDifficulty

TrainingSearchableModel = Union[Training, Section, Asset]


class Command(BaseCommand):
    help = (
        f'Add database objects to the main search index "{settings.MEILISEARCH_INDEX_UID}". '
        f'Also update replica indexes for different search results ordering. The following '
        f'models are indexed: Film, Asset, Training, Section, Post. '
        f'Objects already present in the indexes are updated.'
    )

    def _prepare_data(self) -> Any:
        self.stdout.write('Preparing the data, it may take a while...')

        models_to_index: List[Type[SearchableModel]] = [Film, Asset, Training, Section, Revision]
        objects_to_load: List[SearchableModel] = []
        for model in models_to_index:
            queryset = get_searchable_queryset(model)
            self.stdout.write(f'Preparing {len(queryset)} "{model._meta.label}" objects...')
            qs_values = queryset.values()

            for instance_dict, instance in zip(qs_values, queryset):
                set_individual_fields(instance_dict, instance)

            objects_to_load.extend(qs_values)
            self.stdout.write(f'Done ({len(qs_values)} objects).')

        self.stdout.write(f'{len(objects_to_load)} objects to load')

        # TODO(Natalia): Any better way to serialize datetime objects?
        return json.loads(json.dumps(objects_to_load, cls=DjangoJSONEncoder))

    def _prepare_training_data(self) -> Any:
        self.stdout.write('Preparing the training data, it may take a while...')

        models_to_index: List[Type[TrainingSearchableModel]] = [Training, Section, Asset]
        objects_to_load: List[TrainingSearchableModel] = []

        for model in models_to_index:
            queryset = get_searchable_queryset_for_training(model)
            self.stdout.write(f'Preparing {len(queryset)} "{model._meta.label}" objects...')
            qs_values = queryset.values()
            for instance_dict, instance in zip(qs_values, queryset):
                set_individual_fields_for_training(instance_dict, instance)

            objects_to_load.extend(qs_values)
            self.stdout.write(f'Done ({len(qs_values)} objects).')

        # TODO: do we need datetime fields? Don't add them and get rid of JSON encoder?
        return json.loads(json.dumps(objects_to_load, cls=DjangoJSONEncoder))

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        try:
            # Check the server and indexes first, before performing lengthy computations
            check_meilisearch(check_indexes=True)
        except MeiliSearchServiceError as err:
            raise CommandError(err)

        data_to_load = self._prepare_data()
        training_data_to_load = self._prepare_training_data()

        # Update the main index, the replica indexes, and the training index
        indexes_with_ranking_rules = [
            *settings.INDEXES_FOR_SORTING,
            (settings.TRAINING_INDEX_UID, settings.DEFAULT_RANKING_RULES),
        ]
        for index_uid, ranking_rules in indexes_with_ranking_rules:
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
