from django.utils.decorators import method_decorator
from django.views.decorators.http import require_safe
from django.views.generic import ListView, DetailView

from films.models.films import Film


@method_decorator(require_safe, name='dispatch')
class FilmListView(ListView):
    model = Film
    queryset = Film.objects.filter(visibility=True)
    template_name = 'films/films.html'


@method_decorator(require_safe, name='dispatch')
class FilmDetailView(DetailView):
    queryset = Film.objects.filter(visibility=True)
