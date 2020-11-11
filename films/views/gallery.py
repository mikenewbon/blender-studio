"""Render film asset gallery and collections."""
from django.http import HttpResponse, HttpRequest
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from common.queries import has_group
from films.models import Film, Collection, Asset
from films.queries import get_gallery_drawer_context, get_current_asset


@require_safe
def collection_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    """
    Display all the film collections as well as the featured artwork in the gallery.

    **Context:**

    ``film``
        An instance of :model:`films.Film`.
    ``asset``
        An :model:`films.Asset` that's currently selected and will be shown via the JS modal.
        It's necessary to retrieve it in advance so that correct OG meta could be set.
    ``collections``
        A dict of all the film's collections; needed for the drawer menu.

        Structured as follows::

            {
                collection_0: [nested_collection_0, nested_collection_1, ...],
                collection_1: [...],
                ...
            }
    ``featured_artwork``
        A queryset of :model:`films.Asset`-s belonging to the film and marked as featured.
        The featured assets are displayed on entering the gallery; also needed for the
        drawer menu (where the 'Featured Artwork' fake collection is added).
    ``user_can_edit_collection``
        A bool specifying whether the current user should be able to edit
        :model:`films.Collection` items displayed in the drawer menu.
    ``user_can_edit_asset``
        A bool specifying whether the current user should be able to edit
        :model:`films.Asset` items (featured assets displayed on the main gallery page).

    **Template:**

    :template:`films/gallery.html`
    """
    film = get_object_or_404(Film, slug=film_slug)
    drawer_menu_context = get_gallery_drawer_context(film, request.user)

    context = {
        'film': film,
        'user_can_view_asset': (
            request.user.is_authenticated and has_group(request.user, 'subscriber')
        ),
        'user_can_edit_asset': (
            request.user.is_staff and request.user.has_perm('films.change_asset')
        ),
        **drawer_menu_context,
        **get_current_asset(request),
    }

    return render(request, 'films/gallery.html', context)


@require_safe
def collection_detail(request: HttpRequest, film_slug: str, collection_slug: str) -> HttpResponse:
    """
    Display all the published assets in a :model:`films.Collection`.

    **Context:**

    ``film``
        An instance of :model:`films.Film`. The film that the current collection belongs to.
    ``asset``
        An :model:`films.Asset` that's currently selected and will be shown via the JS modal.
        It's necessary to retrieve it in advance so that correct OG meta could be set.
    ``current_collection``
        An instance of :model:`films.Collection`.
    ``current_assets``
        A queryset of published assets in the current_collection,
        ordered by ``order``, ``date_created``.
    ``collections``
        A dict of all the film's collections; needed for the drawer menu.

        Structured as follows::

            {
                collection_0: [nested_collection_0, nested_collection_1, ...],
                collection_1: [...],
                ...
            }
    ``featured_artwork``
        A queryset of :model:`films.Asset`-s belonging to the film and marked as featured;
        needed for the drawer menu (where the 'Featured Artwork' fake collection is added).
    ``user_can_edit_collection``
        A bool specifying whether the current user should be able to edit
        :model:`films.Collection` items displayed in the drawer menu.
    ``user_can_edit_asset``
        A bool specifying whether the current user should be able to edit
        :model:`films.Asset` items displayed in the collection page.

    **Template:**

    :template:`films/collection_detail.html`
    """
    film = get_object_or_404(Film, slug=film_slug)
    if not request.user.is_superuser and not film.is_published:
        raise Http404("Film does not exist")
    collection = get_object_or_404(Collection, slug=collection_slug, film_id=film.id)
    child_collections = collection.child_collections.order_by(*Collection._meta.ordering)
    drawer_menu_context = get_gallery_drawer_context(film, request.user)

    context = {
        'film': film,
        'current_collection': collection,
        'current_assets': (
            collection.assets.filter(is_published=True).order_by(*Asset._meta.ordering)
        ),
        'child_collections': child_collections,
        'user_can_view_asset': (
            request.user.is_authenticated and has_group(request.user, 'subscriber')
        ),
        'user_can_edit_asset': (
            request.user.is_staff and request.user.has_perm('films.change_asset')
        ),
        **drawer_menu_context,
        **get_current_asset(request),
    }

    return render(request, 'films/collection_detail.html', context)
