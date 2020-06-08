from django.shortcuts import get_object_or_404, render

from films.models import Film


def film_collection_list(request, slug):
    film = get_object_or_404(Film, slug=slug)
    context = {'film': film, 'collections': film.collections.filter(parent__isnull=True)}
    return render(request, 'films/gallery.html', context)
