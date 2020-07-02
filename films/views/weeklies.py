from typing import Optional, Union

from django.core.paginator import Paginator
from django.db.models.query import Prefetch, QuerySet
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film, ProductionLog, ProductionLogEntryAsset

DEFAULT_LOGS_PAGE_SIZE = 3


def get_production_logs_for_context(
    film: Film,
    page_number: Optional[Union[int, str]] = 1,
    per_page: Optional[Union[int, str]] = DEFAULT_LOGS_PAGE_SIZE,
) -> 'QuerySet[ProductionLog]':
    """Retrieve production logs for film weeklies context.

    Altogether, this function sends 5 database queries.

    Args:
        film: A Film model instance
        page_number: (optional) int; production logs page number, used by the paginator.
            By default, the first page.
        per_page: (optional) int or str; the number of logs to display per page, used
            by the paginator. Defaults to DEFAULT_LOGS_PAGE_SIZE.

    Returns:
        A queryset containing production logs and all their related objects used in templates:
         - production log entries,
         - entries' authors and users (used to get each entry's author_name),
         - assets and static assets related to log entries. Note that entries' related
            `entry_assets` are available under the `assets` attribute (set in Prefetch).
            These objects are stored in a Python list, which is supposed to improve
            performance (see the note in the docs:
            https://docs.djangoproject.com/en/dev/ref/models/querysets/#django.db.models.Prefetch).
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
    paginator = Paginator(production_logs, per_page)
    production_logs_page = paginator.get_page(page_number)

    return production_logs_page


def production_log_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    page_number = request.GET.get('page')
    per_page = request.GET.get('per_page')
    context = {
        'film': film,
        'production_logs': get_production_logs_for_context(film, page_number, per_page),
    }

    return render(request, 'films/weeklies.html', context)
