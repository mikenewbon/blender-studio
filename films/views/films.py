from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_safe
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from films.models import Film


@method_decorator(require_safe, name='dispatch')
class FilmListView(ListView):
    model = Film
    queryset = Film.objects.filter(is_published=True).order_by('status', '-release_date')
    template_name = 'films/films.html'


@method_decorator(require_safe, name='dispatch')
class FilmDetailView(DetailView):
    queryset = Film.objects.filter(is_published=True)
    slug_url_kwarg = 'film_slug'


def about(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {'film': film}
    return render(request, 'films/about.html', context)


def weeklies(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {'film': film}
    return render(request, 'films/weeklies.html', context)
