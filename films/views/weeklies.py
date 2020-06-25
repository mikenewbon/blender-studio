from django.core.paginator import Page, Paginator
from django.db.models.query import Prefetch, QuerySet
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film, ProductionLog, ProductionLogEntryAsset

DEFAULT_LOGS_PAGE_SIZE = 3


def get_production_logs_for_context(film: Film) -> 'QuerySet[ProductionLog]':
    """Retrieve production logs for film weeklies context.

    The returned queryset contains production logs and all their related objects
    used in templates:
     - production log entries (under the `entries` attribute of a production log),
     - assets and static assets related to log entries,
     - entries authors and users (used to get each entry's author_name).
    Altogether, this function sends 5 database queries.
    """
    production_logs = film.production_logs.order_by('-start_date').prefetch_related(
        'log_entries__author',
        'log_entries__user',
        Prefetch(
            'log_entries__entry_assets',
            queryset=ProductionLogEntryAsset.objects.select_related('asset__static_asset').order_by(
                'asset__date_created'
            ),
            to_attr='assets',
        ),
    )
    production_log_dict = {}
    for log in production_logs:
        production_log_dict[log] = {}
        for entry in log.log_entries.all():
            production_log_dict[log][entry] = [entry_asset.asset for entry_asset in entry.assets]

    # TODO(Natalia): paginator accepts a query set, not a dict
    # page_number = request.GET.get('page')
    # paginator = Paginator(production_logs, page_size)
    # production_logs_page = paginator.get_page(page_number)

    return production_log_dict


def production_log_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {
        'film': film,
        'production_logs': get_production_logs_for_context(film),
    }

    return render(request, 'films/weeklies.html', context)
