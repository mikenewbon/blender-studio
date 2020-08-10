from typing import Optional, Any

import meilisearch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

SEARCHABLE_ATTRIBUTES = [
    # Model fields/annotations that are searchable:
    #     Film: ['model', 'name', 'project', 'description', 'summary'],
    #     Asset: ['model', 'name', 'project', 'collection_name', 'description'],
    #     Training: ['model', 'name', 'project', 'description', 'summary'],
    #     Section: ['model', 'name', 'project', 'chapter_name', 'description'],
    #     Post: ['model', 'name', 'project', 'topic', 'description', 'content']
    # In the order of relevance:
    'model',
    'name',
    'project',
    'topic',
    'collection_name',
    'chapter_name',
    'description',
    'summary',
    'content',
]
FACETING_ATTRIBUTES = ['model', 'project', 'license', 'media_type']


class Command(BaseCommand):
    help = 'Create a search index, or update its settings if it already exists.'

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
        try:
            index = client.create_index(
                settings.MEILISEARCH_INDEX_NAME, {'primaryKey': 'search_id'}
            )
        except meilisearch.errors.MeiliSearchCommunicationError:
            raise CommandError(
                f'Failed to establish a new connection with MeiliSearch API at '
                f'{settings.MEILISEARCH_API_ADDRESS}. Make sure that the server is running.'
            )
        except meilisearch.errors.MeiliSearchApiError as err:
            if err.error_code != 'index_already_exists':
                raise CommandError(err)
            index = client.get_index(settings.MEILISEARCH_INDEX_NAME)
            self.stdout.write(
                f'The index "{settings.MEILISEARCH_INDEX_NAME}" already exists. '
                f'Skipping creation...'
            )
        else:
            self.stdout.write(
                f'Successfully created the index "{settings.MEILISEARCH_INDEX_NAME}".'
            )

        index.update_settings({'searchableAttributes': SEARCHABLE_ATTRIBUTES})
        index.update_attributes_for_faceting(FACETING_ATTRIBUTES)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated the index "{settings.MEILISEARCH_INDEX_NAME}".'
            )
        )

        return None
