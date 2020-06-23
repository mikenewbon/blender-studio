from django.db.models import prefetch_related_objects
from django.db.models.query import Prefetch
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film


def production_log_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    production_logs = film.production_logs.order_by('-start_date').prefetch_related(
        Prefetch('log_entries', to_attr='entries')
    )
    prefetch_related_objects(production_logs, 'entries__entry_assets__asset__static_asset')
    # Altogether, 6 database queries are executed to retrieve te film, logs and assets.

    context = {
        "film": film,
        "production_logs": production_logs,
    }

    return render(request, 'films/weeklies.html', context)
