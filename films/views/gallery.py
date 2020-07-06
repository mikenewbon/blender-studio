from typing import Dict, Any

from django.db.models import QuerySet
from django.db.models.query import Prefetch
from django.http import HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404, render

from films.models import Film, Collection, Asset


def get_gallery_drawer_context(film: Film) -> Dict[str, Any]:
    """Retrieves collections for drawer menu in gallery.

    The collections are ordered and nested, ready to be looped over in templates.
    Also the fake 'Featured Artwork' collection is created.
    This function sends TWO database queries (1: fetch film top-level collections,
    2: fetch their child collections, ordered).
    Returns a dictionary:
    'collections': <a dict of all the collections with their nested collections>,
    'featured_artwork': <a queryset of film assets marked as featured>.
    """
    top_level_collections = (
        film.collections.filter(parent__isnull=True)
        .order_by('order', 'name')
        .prefetch_related(
            Prefetch(
                'child_collections',
                queryset=film.collections.order_by('order', 'name'),
                to_attr='nested',
            )
        )
    )

    nested_collections: Dict[Collection, QuerySet[Collection]] = dict()
    for c in top_level_collections:
        nested_collections[c] = c.nested  # type: ignore[attr-defined]

    return {
        'collections': nested_collections,
        'featured_artwork': film.assets.filter(is_featured=True, is_published=True).order_by(
            'date_created'
        ),
    }


def collection_list(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug)
    drawer_menu_context = get_gallery_drawer_context(film)

    context = {
        'film': film,
        **drawer_menu_context,
    }

    return render(request, 'films/gallery.html', context)


def collection_detail(request: HttpRequest, film_slug: str, collection_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    collection = get_object_or_404(Collection, slug=collection_slug, film_id=film.id)
    child_collections = collection.child_collections.order_by('order', 'name')
    drawer_menu_context = get_gallery_drawer_context(film)

    context = {
        'film': film,
        'current_collection': collection,
        'current_assets': collection.assets.filter(is_published=True)
        .order_by('order', 'name')
        .select_related('static_asset__storage_location'),
        'child_collections': child_collections,
        **drawer_menu_context,
    }

    return render(request, 'films/collection_detail.html', context)


def asset_detail(request: HttpRequest, film_slug: str, asset_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    asset = get_object_or_404(Asset, slug=asset_slug, film_id=film.id, is_published=True)

    return render(request, 'films/asset_detail.html', {'film': film, 'asset': asset})
