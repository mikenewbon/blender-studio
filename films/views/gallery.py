from typing import List, Dict

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404, render

from films.models import Film, Collection, Asset


def film_collection_list(request, slug):
    film = get_object_or_404(Film, slug=slug)
    top_collections = (
        film.collections.filter(parent__isnull=True)
        .order_by('order')
        .prefetch_related('child_collections')
    )

    nested_collections: Dict[Collection, QuerySet[Collection]] = dict()
    for c in top_collections:
        nested_collections[c] = c.child_collections.all()

    static_assets = film.storage.assets.prefetch_related('assets')
    featured_artwork: List[Asset] = []
    for asset in static_assets:
        featured_artwork.extend(asset.assets.filter(is_featured=True))

    context = {
        'film': film,
        'collections': nested_collections,
        'featured_artwork': film.assets.filter(is_featured=True),
    }

    return render(request, 'films/gallery.html', context)
