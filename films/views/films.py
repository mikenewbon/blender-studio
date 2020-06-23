from django.db.models.query import Prefetch
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_safe
from django.views.generic.list import ListView

from films.models import Film
from films.views.weeklies import get_production_logs_for_context


@method_decorator(require_safe, name='dispatch')
class FilmListView(ListView):
    model = Film
    queryset = Film.objects.filter(is_published=True).order_by('status', '-release_date')
    template_name = 'films/films.html'


@require_safe
def film_detail(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    featured_artwork = film.assets.filter(is_published=True, is_featured=True)

    context = {
        'film': film,
        'featured_artwork': featured_artwork,
        'production_logs': get_production_logs_for_context(film),
    }

    return render(request, 'films/film_detail.html', context)


@require_safe
def about(request: HttpRequest, film_slug: str) -> HttpResponse:
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    context = {'film': film}
    return render(request, 'films/about.html', context)
