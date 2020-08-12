import ast
from enum import Enum
from typing import Dict

import meilisearch
from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe, require_POST


@require_safe
def api_search(request: HttpRequest) -> JsonResponse:
    client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
    index = client.get_index(settings.MEILISEARCH_INDEX_UID)
    query = request.GET.get('q', '')

    opt_params = {k: v for k, v in request.GET.items() if k != 'q'}

    for param in opt_params:
        opt_params[param] = ast.literal_eval(opt_params[param])

    results = index.search(query=query, opt_params=opt_params)

    return JsonResponse({'results': results})


class SortingParams(Enum):
    """Defines possible values of the sorting_param for search results."""

    RELEVANCE = 'relevance'
    DATE_DESC = 'date_desc'
    DATE_ASC = 'date_asc'
    default = RELEVANCE


@require_POST
@csrf_exempt
def api_search_sort(request: HttpRequest, sorting_param: str) -> JsonResponse:
    client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
    index = client.get_index(settings.MEILISEARCH_INDEX_UID)
    default_ranking_rules = [
        'typo',
        'words',
        'proximity',
        'attribute',
        'wordsPosition',
        'exactness',
    ]

    if sorting_param == SortingParams.DATE_DESC.value:
        ranking_rules = ['desc(date_created_ts)', *default_ranking_rules]
    elif sorting_param == SortingParams.DATE_ASC.value:
        ranking_rules = ['asc(date_created_ts)', *default_ranking_rules]
    else:
        ranking_rules = default_ranking_rules

    update_data: Dict[str, int] = index.update_ranking_rules(ranking_rules)

    return JsonResponse(update_data)


@require_safe
def search(request: HttpRequest) -> HttpResponse:

    return render(request, 'search/search.html', {})
