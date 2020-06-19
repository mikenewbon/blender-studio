from django.db.models.query import Prefetch
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film, ProductionLog


def production_log_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    production_logs = (
        ProductionLog.objects.select_related('film')
        .filter(film_id=film.id)
        .order_by('-start_date')
        .prefetch_related(Prefetch('log_entries', to_attr='entries'))
    )
    context = {
        "film": film,
        "production_logs": production_logs,
    }

    return render(request, 'films/weeklies.html', context)
