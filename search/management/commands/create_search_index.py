from typing import Optional, Any

import meilisearch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        f'Create the main search index "{settings.MEILISEARCH_INDEX_UID}" and replica indexes, '
        f'or update their settings if they already exist.'
    )

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        client = settings.SEARCH_CLIENT

        # Create or update the main index and the replica indexes
        for index_uid, ranking_rules in settings.INDEXES_FOR_SORTING:
            try:
                index = client.create_index(index_uid, {'primaryKey': 'search_id'})
            except meilisearch.errors.MeiliSearchCommunicationError:
                raise CommandError(
                    f'Failed to establish a new connection with MeiliSearch API at '
                    f'{settings.MEILISEARCH_API_ADDRESS}. Make sure that the server is running.'
                )
            except meilisearch.errors.MeiliSearchApiError as err:
                if err.error_code != 'index_already_exists':
                    raise CommandError(err)
                index = client.get_index(index_uid)
                self.stdout.write(f'The index "{index_uid}" already exists. Skipping creation...')
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created the index "{index_uid}".')
                )

            index.update_ranking_rules(ranking_rules)
            index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)
            index.update_attributes_for_faceting(settings.FACETING_ATTRIBUTES)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated the index "{index_uid}".'))

        return None
