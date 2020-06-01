from django.urls import path

from films.views.films.film import FilmListView, FilmDetailView

urlpatterns = [
    path('', FilmListView.as_view(), name='film-list'),
    path('<slug:slug>', FilmDetailView.as_view(), name='film-detail'),
]
