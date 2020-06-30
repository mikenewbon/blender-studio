from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from films.models import Film
from films.views.weeklies import get_production_logs_for_context, DEFAULT_LOGS_PAGE_SIZE


@require_safe
def production_logs_page(request: HttpRequest, film_pk: int) -> HttpResponse:
    film = get_object_or_404(Film, id=film_pk, is_published=True)
    page_size = request.GET.get('page_size', DEFAULT_LOGS_PAGE_SIZE)
    production_logs_page = get_production_logs_for_context(request, film, page_size)
    context = {'production_logs_page': production_logs_page}

    return render(request, 'films/components/activity_feed.html', context)
