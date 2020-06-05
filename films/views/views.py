from django.shortcuts import render, get_object_or_404

from films.models import Film


def about(request, slug):
    film = get_object_or_404(Film, slug=slug)
    context = {'film': film}
    return render(request, 'films/about.html', context)


def gallery(request, slug):
    film = get_object_or_404(Film, slug=slug)
    context = {'film': film}
    return render(request, 'films/gallery.html', context)


def weeklies(request, slug):
    film = get_object_or_404(Film, slug=slug)
    context = {'film': film}
    return render(request, 'films/weeklies.html', context)
