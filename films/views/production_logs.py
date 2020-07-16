from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film
from films.views.api.production_logs import get_production_logs_page


def production_log_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    """
    Displays the latest production logs for the :model:`films.Film` with the given slug.

    Also fetches the related log entries (:model:`films.ProductionLogEntry`), and
    the assets (:model:`films.Asset`) they contain.

    **Context:**

    ``film``
        An instance of :model:`films.Film`.
    ``production_logs_page``
        A single page of the latest production logs for the ``film``, sorted by their
        descending ``date_created``.
    ``show_more_button``
        A bool set to True. Has to have a truthy value for the 'Load more weeks' button
        to be displayed in the :template:`films/components/activity_feed.html` template.
    ``user_can_edit_production_log``
        A bool specifying whether the current user should be able to edit
        :model:`films.ProductionLog` items displayed in the Weeklies section of the page.
    ``user_can_edit_production_log_entry``
        A bool specifying whether the current user should be able to edit
        :model:`films.ProductionLogEntry` items in the production logs.
    ``user_can_edit_asset``
        A bool specifying whether the current user should be able to edit
        :model:`films.Asset` items displayed in the production log entries.

    **Template:**

    :template:`films/production_logs.html`
    """
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {
        'film': film,
        'production_logs_page': get_production_logs_page(film),
        'show_more_button': True,
        'user_can_edit_production_log': (
            request.user.is_staff and request.user.has_perm('films.change_production_log')
        ),
        'user_can_edit_production_log_entry': (
            request.user.is_staff and request.user.has_perm('films.change_production_log_entry')
        ),
        'user_can_edit_asset': (
            request.user.is_staff and request.user.has_perm('films.change_asset')
        ),
    }

    return render(request, 'films/production_logs.html', context)
