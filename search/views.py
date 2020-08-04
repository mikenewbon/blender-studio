import ast

import meilisearch
from django.http.request import HttpRequest
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_safe


@require_POST
def api_search(request: HttpRequest) -> JsonResponse:
    client = meilisearch.Client('http://127.0.0.1:7700')
    index = client.get_index('studio')
    query = request.GET.get('q', '')

    opt_params = {k: v for k, v in request.GET.items() if k != 'q'}

    for param in opt_params:
        opt_params[param] = ast.literal_eval(opt_params[param])

    results = index.search(query=query, opt_params=opt_params)

    return JsonResponse({'results': results})


@require_safe
def search(request: HttpRequest) -> HttpResponse:

    return render(request, 'search/search.html', {})
