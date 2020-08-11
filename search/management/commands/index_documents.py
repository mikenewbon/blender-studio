import json
from typing import List
from typing import Optional, Any

import meilisearch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import Model

from blog.models import Post
from films.models import Film, Asset
from search.management.commands.create_search_index import SEARCHABLE_ATTRIBUTES
from search.queries import (
    get_searchable_films,
    get_searchable_assets,
    get_searchable_trainings,
    get_searchable_sections,
    get_searchable_posts,
    set_thumbnail_url,
    add_common_annotations,
)
from training.models import Training, Section


class Command(BaseCommand):
    help = (
        f'Add database objects to the search index "{settings.MEILISEARCH_INDEX_NAME}". '
        f'Indexes the following models: Film, Asset, Training, Section, Post. '
        f'If an object already exists in the index, it is updated.'
    )

    def prepare_data(self) -> Any:
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

            for obj_dict, obj in zip(qs_values, queryset):
                set_thumbnail_url(obj_dict, obj)

            objects_to_load.extend(qs_values)

        self.stdout.write(f'{len(objects_to_load)} objects to load')

        # TODO(Natalia): Any better way to serialize datetime objects?
        return json.loads(json.dumps(objects_to_load, cls=DjangoJSONEncoder))

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
        index = client.get_index(settings.MEILISEARCH_INDEX_NAME)

        data_to_load = self.prepare_data()

        try:
            index.add_documents(data_to_load)
        except meilisearch.errors.MeiliSearchCommunicationError:
            raise CommandError(
                f'Failed to establish a new connection with MeiliSearch API at '
                f'{settings.MEILISEARCH_API_ADDRESS}. Make sure that the server is running.'
            )
        except meilisearch.errors.MeiliSearchApiError:
            raise CommandError(
                f'Error accessing the index "{settings.MEILISEARCH_INDEX_NAME}" of the client '
                f'at {self.MEILISEARCH_API_ADDRESS}. Make sure that the index exists.'
            )

        # There seems to be no way in MeiliSearch v0.13 to disable adding new document
        # fields automatically to searchable attrs, so we update the settings to set them:
        index.update_settings({'searchableAttributes': SEARCHABLE_ATTRIBUTES})

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated the index "{settings.MEILISEARCH_INDEX_NAME}".'
            )
        )

        return None
