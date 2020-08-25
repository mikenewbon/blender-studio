from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
def search(request: HttpRequest) -> HttpResponse:
    """"""
    return render(request, 'search/search.html', {})
