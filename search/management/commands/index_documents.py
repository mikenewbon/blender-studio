import json
from typing import List
from typing import Optional, Any

import meilisearch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import Model

from blog.models import Post
from films.models import Film, Asset
from search.queries import (
    get_searchable_films,
    get_searchable_assets,
    get_searchable_trainings,
    get_searchable_sections,
    get_searchable_posts,
    set_thumbnail_and_url,
    add_common_annotations,
)
from training.models import Training, Section


class Command(BaseCommand):
    help = (
        f'Add database objects to the specified search index '
        f'("{settings.MEILISEARCH_INDEX_UID}" by default). Also create replica'
        f'indexes for different search results ordering.'
        f'Indexes the following models: Film, Asset, Training, Section, Post. '
        f'If an object already exists in the index, it is updated.'
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--index',
            default=settings.MEILISEARCH_INDEX_UID,
            help='The uid of the index to which to add the documents. '
            'The index has to exist already.',
        )

    def _prepare_data(self) -> Any:
        self.stdout.write('Preparing the data, it may take a while...')

        models_and_querysets = {
            Film: get_searchable_films(),
            Asset: get_searchable_assets(),
            Training: get_searchable_trainings(),
            Section: get_searchable_sections(),
            Post: get_searchable_posts(),
        }

        objects_to_load: List[Model] = []
        for model, queryset in models_and_querysets.items():
            queryset = add_common_annotations(queryset)
            qs_values = queryset.values()

            for instance_dict, instance in zip(qs_values, queryset):
                set_thumbnail_and_url(instance_dict, instance)

            objects_to_load.extend(qs_values)

        self.stdout.write(f'{len(objects_to_load)} objects to load')

        # TODO(Natalia): Any better way to serialize datetime objects?
        return json.loads(json.dumps(objects_to_load, cls=DjangoJSONEncoder))

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        index_uid = options['index']
        index = settings.SEARCH_CLIENT.get_index(index_uid)

        data_to_load = self._prepare_data()

        try:
            response = index.add_documents(data_to_load)
        except meilisearch.errors.MeiliSearchCommunicationError:
            raise CommandError(
                f'Failed to establish a new connection with MeiliSearch API at '
                f'{settings.MEILISEARCH_API_ADDRESS}. Make sure that the server is running.'
            )
        except meilisearch.errors.MeiliSearchApiError:
            raise CommandError(
                f'Error accessing the index "{index_uid}" of the client '
                f'at {settings.MEILISEARCH_API_ADDRESS}. Make sure that the index exists.'
            )

        # There seems to be no way in MeiliSearch v0.13 to disable adding new document
        # fields automatically to searchable attrs, so we update the settings to set them:
        index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated the index "{index_uid}". '
                f'Update ID is {response["updateId"]}.'
            )
        )

        # Restore default ranking rules
        index.update_ranking_rules(settings.DEFAULT_RANKING_RULES)

        # Create or update replica indexes (for sorting)
        for replica_uid, ranking_rules in settings.REPLICA_INDEXES_FOR_SORTING:
            replica_index = settings.SEARCH_CLIENT.get_or_create_index(replica_uid)
            replica_index.add_documents(data_to_load)
            replica_index.update_ranking_rules(ranking_rules)
            replica_index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)
            replica_index.update_attributes_for_faceting(settings.FACETING_ATTRIBUTES)

            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated the replica index "{replica_uid}". ')
            )

        return str(response["updateId"])
