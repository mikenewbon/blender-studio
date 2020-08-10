from typing import Optional, Any

import meilisearch
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

    API_address: str = 'http://127.0.0.1:7700'
    index_name: str = 'studio'

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        client = meilisearch.Client(self.API_address)
        try:
            index = client.create_index(self.index_name, {'primaryKey': 'search_id'})
        except meilisearch.errors.MeiliSearchCommunicationError:
            raise CommandError(
                f'Failed to establish a new connection with MeiliSearch API at '
                f'{self.API_address}. Make sure that the server is running.'
            )
        except meilisearch.errors.MeiliSearchApiError as err:
            if err.error_code != 'index_already_exists':
                raise CommandError(err)
            index = client.get_index(self.index_name)
            self.stdout.write(f'The index "{self.index_name}" already exists. Skipping creation...')
        else:
            self.stdout.write(f'Successfully created the index "{self.index_name}".')

        index.update_settings({'searchableAttributes': SEARCHABLE_ATTRIBUTES})
        index.update_attributes_for_faceting(FACETING_ATTRIBUTES)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated the index "{self.index_name}".')
        )

        return None
