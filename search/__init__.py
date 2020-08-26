from typing import List

from django.conf import settings

from common.types import assert_cast

default_app_config = 'search.apps.SearchConfig'


MAIN_INDEX_UIDS: List[str] = list(assert_cast(dict, settings.MAIN_SEARCH['RANKING_RULES']).keys())
TRAINING_INDEX_UIDS: List[str] = list(
    assert_cast(dict, settings.TRAINING_SEARCH['RANKING_RULES']).keys()
)
ALL_INDEX_UIDS = [*MAIN_INDEX_UIDS, *TRAINING_INDEX_UIDS]
