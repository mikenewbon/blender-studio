from django.db.models import prefetch_related_objects, QuerySet
from django.db.models.query import Prefetch
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film, ProductionLog


def get_production_logs_for_context(film: Film) -> 'QuerySet[ProductionLog]':
    """A helper function that retrieves production logs for film weeklies context.

    The returned queryset contains production logs and all their related objects
    used in templates:
     - production log entries (under the `entries` attribute of a production log),
     - assets and static assets related to log entries,
     - entries authors and users (used to get each entry's author_name).
    Altogether, this function sends 7 database queries.
    """
    production_logs = film.production_logs.order_by('-start_date').prefetch_related(
        Prefetch('log_entries', to_attr='entries')
    )
    prefetch_related_objects(
        production_logs,
        'entries__author',
        'entries__user',
        'entries__entry_assets__asset__static_asset',
    )

    return production_logs


def production_log_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {
        'film': film,
        'production_logs': get_production_logs_for_context(film),
    }

    return render(request, 'films/weeklies.html', context)
