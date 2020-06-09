from typing import Dict

from django.db.models import QuerySet
from django.db.models.query import Prefetch
from django.shortcuts import get_object_or_404, render

from films.models import Film, Collection


def film_collection_list(request, slug):
    film = get_object_or_404(Film, slug=slug)
    top_level_collections = (
        film.collections.filter(parent__isnull=True)
        .order_by('order')
        .prefetch_related(
            Prefetch(
                'child_collections', queryset=film.collections.order_by('order'), to_attr='nested'
            )
        )
    )

    nested_collections: Dict[Collection, QuerySet[Collection]] = dict()
    for c in top_level_collections:
        nested_collections[c] = c.nested

    context = {
        'film': film,
        'collections': nested_collections,
        'featured_artwork': film.assets.filter(is_featured=True, is_published=True),
    }

    return render(request, 'films/gallery.html', context)
