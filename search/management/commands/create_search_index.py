from typing import Optional, Any

import meilisearch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from search.health_check import MeiliSearchServiceError, check_meilisearch


class Command(BaseCommand):
    help = (
        f'Create the main search index "{settings.MEILISEARCH_INDEX_UID}" and replica indexes, '
        f'or update their settings if they already exist.'
    )

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        try:
            check_meilisearch()
        except MeiliSearchServiceError as err:
            raise CommandError(err)

        # Create or update the main index, the replica indexes, and the training index
        indexes_with_ranking_rules = [
            *settings.INDEXES_FOR_SORTING,
            (settings.TRAINING_INDEX_UID, settings.DEFAULT_RANKING_RULES),
        ]
        for index_uid, ranking_rules in indexes_with_ranking_rules:
            try:
                index = settings.SEARCH_CLIENT.create_index(index_uid, {'primaryKey': 'search_id'})
            except meilisearch.errors.MeiliSearchApiError as err:
                if err.error_code != 'index_already_exists':
                    raise CommandError(err)
                index = settings.SEARCH_CLIENT.get_index(index_uid)
                self.stdout.write(f'The index "{index_uid}" already exists. Skipping creation...')
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created the index "{index_uid}".')
                )

            index.update_ranking_rules(ranking_rules)
            if index_uid == settings.TRAINING_INDEX_UID:
                index.update_searchable_attributes(settings.TRAINING_SEARCHABLE_ATTRIBUTES)
                index.update_attributes_for_faceting(settings.TRAINING_FACETING_ATTRIBUTES)
            else:
                index.update_searchable_attributes(settings.SEARCHABLE_ATTRIBUTES)
                index.update_attributes_for_faceting(settings.FACETING_ATTRIBUTES)

            self.stdout.write(self.style.SUCCESS(f'Successfully updated the index "{index_uid}".'))

        return None
