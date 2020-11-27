# noqa: D100
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_safe

from common.queries import has_active_subscription
from films.models import Film, FilmFlatPage, Asset
from films.queries import get_production_logs_page, get_current_asset


@require_safe
def film_list(request: HttpRequest) -> HttpResponse:
    """
    Display all the published films.

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
        'films': (Film.objects.order_by('status', '-release_date')),
        'user_can_edit_film': (
            request.user.is_staff and request.user.has_perm('films.change_film')
        ),
    }

    return render(request, 'films/films.html', context)


@require_safe
def film_detail(request: HttpRequest, film_slug: str) -> HttpResponse:
    """
    Display the detail page of the :model:`films.Film` specified by the given slug.

    **Context:**

    ``film``
        An instance of :model:`films.Film`.
    ``asset``
        An :model:`films.Asset` that's currently selected and will be shown via the JS modal.
        It's necessary to retrieve it in advance so that correct OG meta could be set.
    ``featured_artwork``
        A queryset of :model:`films.Asset`-s belonging to the film and marked as featured.
    ``production_logs_page`` (only for non-released films!)
        A single page of the latest production logs for the ``film``, sorted by their
        descending ``date_created``. Added to the context only if the film's status
        is **different** than 'Released' -- i.e. 'In Development' or 'In Production'.
    ``user_can_edit_film``
        A bool specifying whether the current user should be able to edit the
        :model:`films.Film` displayed in the page.
    ``user_can_edit_asset``
        A bool specifying whether the current user should be able to edit
        :model:`films.Asset`-s displayed in the page.

    **Template:**

    :template:`films/film_detail.html`
    """
    film = get_object_or_404(Film, slug=film_slug)
    featured_artwork = film.assets.filter(is_featured=True).order_by(*Asset._meta.ordering)

    context = {
        'film': film,
        'featured_artwork': featured_artwork,
        'user_can_view_asset': (
            request.user.is_authenticated and has_active_subscription(request.user)
        ),
        'user_can_edit_film': (
            request.user.is_staff and request.user.has_perm('films.change_film')
        ),
        'user_can_edit_asset': (
            request.user.is_staff and request.user.has_perm('films.change_asset')
        ),
        **get_current_asset(request),
    }
    if film.show_production_logs_as_featured:
        context['production_logs_page'] = get_production_logs_page(film)

    return render(request, 'films/film_detail.html', context)


@require_safe
def flatpage(request: HttpRequest, film_slug: str, page_slug: str) -> HttpResponse:
    """
    Display the "About" page of the :model:`films.Film` specified by the given slug.

    **Context:**

    ``film``
        A :model:`films.Film` instance; the film that the flatpage belongs to.
    ``flatpage``
        A :model:`films.FilmFlatPage` instance.
    ``user_can_edit_film``
        A bool specifying whether the current user is able to edit the
        :model:`films.Film` to which the page belongs.
    ``user_can_edit_flatpage``
        A bool specifying whether the current user is able to edit the
        :model:`films.FilmFlatPage` displayed in the page.

    **Template:**

    :template:`films/flatpage.html`
    """
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    flatpage = get_object_or_404(FilmFlatPage, film=film, slug=page_slug)
    context = {
        'film': film,
        'flatpage': flatpage,
        'user_can_edit_film': (
            request.user.is_staff and request.user.has_perm('films.change_film')
        ),
        'user_can_edit_flatpage': (
            request.user.is_staff and request.user.has_perm('films.change_filmflatpage')
        ),
    }
    return render(request, 'films/flatpage.html', context)
