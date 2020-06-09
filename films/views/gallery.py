from django.shortcuts import get_object_or_404, render

from films.models import Film


def film_collection_list(request, slug):
    film = get_object_or_404(Film, slug=slug)
    top_collections = (
        film.collections.filter(parent__isnull=True)
        .order_by('order')
        .prefetch_related('child_collections')
    )

    nested_collections = dict()
    for c in top_collections:
        nested_collections[c] = c.child_collections.all()

    context = {'film': film, 'collections': nested_collections}

    return render(request, 'films/gallery.html', context)
