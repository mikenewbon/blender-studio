from typing import Optional, Union

from django.core import paginator
from django.db.models.query import Prefetch
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from films.models import Film, ProductionLogEntryAsset

DEFAULT_LOGS_PAGE_SIZE = 3


def get_production_logs_page(
    film: Film,
    page_number: Optional[Union[int, str]] = 1,
    per_page: Optional[Union[int, str]] = DEFAULT_LOGS_PAGE_SIZE,
) -> paginator.Page:
    """Retrieve production logs for film production logs context.

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
            queryset=ProductionLogEntryAsset.objects.select_related(
                'asset__static_asset__storage_backend'
            ).order_by('asset__date_created'),
            to_attr='assets',
        ),
    )
    page_number = int(page_number) if page_number else 1
    per_page = int(per_page) if per_page else DEFAULT_LOGS_PAGE_SIZE
    p = paginator.Paginator(production_logs, per_page)
    production_logs_page = p.get_page(page_number)

    return production_logs_page


@require_safe
def production_logs_page(request: HttpRequest, film_pk: int) -> HttpResponse:
    film = get_object_or_404(Film, id=film_pk, is_published=True)
    page_number = request.GET.get('page')
    per_page = request.GET.get('per_page')
    context = {
        'film': film,
        'production_logs_page': get_production_logs_page(film, page_number, per_page),
        'show_more_button': True,
    }

    return render(request, 'films/components/activity_feed.html', context)
