from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_safe

from films.models import Film, FilmStatus
from films.views.api.production_logs import get_production_logs_page


@require_safe
def film_list(request: HttpRequest) -> HttpResponse:
    """
    Displays all the published films.

    **Context:**

    ``films``
        A queryset of published films, ordered by ``status`` and decreasing ``release_date``.
    ``user_can_edit_film``
        A bool specifying whether the current user should be able to edit
        :model:`films.Film`-s displayed in the page.

    **Template:**

    :template:`films/films.html`
    """
    context = {
        'films': (
            Film.objects.filter(is_published=True)
            .select_related('storage_location')
            .order_by('status', '-release_date')
        ),
        'user_can_edit_film': (
            request.user.is_staff and request.user.has_perm('films.change_film')
        ),
    }

    return render(request, 'films/films.html', context)


@require_safe
def film_detail(request: HttpRequest, film_slug: str) -> HttpResponse:
    """
    Displays the detail page of the :model:`films.Film` specified by the given slug.

    **Context:**

    ``film``
        An instance of :model:`films.Film`.
    ``featured_artwork``
        A queryset of :model:`films.Asset`-s belonging to the film and marked as featured.
    ``production_logs_page`` (only for non-released films!)
        A single page of the latest production logs for the ``film``, sorted by their
        descending ``date_created``. Added to the context only if the film's status
        is **different** than 'Released' -- i.e. 'In Development' or 'In Production'.
    ``user_can_edit_film``
        A bool specifying whether the current user should be able to edit the
        :model:`films.Film` displayed in the page.

    **Template:**

    :template:`films/film_detail.html`
    """
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    featured_artwork = film.assets.filter(is_published=True, is_featured=True)

    context = {
        'film': film,
        'featured_artwork': featured_artwork,
        'user_can_edit_film': (
            request.user.is_staff and request.user.has_perm('films.change_film')
        ),
    }
    if film.status != FilmStatus.released:
        context['production_logs_page'] = get_production_logs_page(film)

    return render(request, 'films/film_detail.html', context)


@require_safe
def about(request: HttpRequest, film_slug: str) -> HttpResponse:
    """
    Displays the "About" page of the :model:`films.Film` specified by the given slug.

    **Context:**

    ``film``
        An instance of :model:`films.Film`.
    ``user_can_edit_film``
        A bool specifying whether the current user should be able to edit the
        :model:`films.Film` displayed in the page.

    **Template:**

    :template:`films/about.html`
    """
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {
        'film': film,
        'user_can_edit_film': (
            request.user.is_staff and request.user.has_perm('films.change_film')
        ),
    }
    return render(request, 'films/about.html', context)
