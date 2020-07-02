from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film
from films.views.api.production_logs import get_production_logs_page


def production_log_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {
        'film': film,
        'production_logs_page': get_production_logs_page(film),
        'show_more_button': True,
    }

    return render(request, 'films/weeklies.html', context)
