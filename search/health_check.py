from typing import Optional

import meilisearch
from django.conf import settings


class MeiliSearchServiceError(Exception):
    pass


def check_meilisearch(check_indexes: Optional[bool] = False) -> None:
    """Checks if MeiliSearch server is running and (optionally) if necessary indexes exist.

    Args:
        check_indexes: bool specifying whether to also check for the default indexes existence,

    Raises:
        MeiliSearchServiceError if server communication fails or if some indexes don't exist.
    """
    try:
        indexes = settings.SEARCH_CLIENT.get_indexes()
    except meilisearch.errors.MeiliSearchCommunicationError:
        raise MeiliSearchServiceError(
            f'Failed to establish a new connection with MeiliSearch API at '
            f'{settings.MEILISEARCH_API_ADDRESS}. Make sure that the server is running.'
        )
    if check_indexes:
        index_uids = [i['name'] for i in indexes]
        missing_uids = [i for i in settings.ALL_INDEXES_UIDS if i not in index_uids]
        if missing_uids:
            raise MeiliSearchServiceError(
                f'Some of the expected indexes do not exist: {missing_uids}. Run the '
                f'`create_search_indexes` command to create them first.'
            )
