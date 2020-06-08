from django.urls import path

from films.views import films
from films.views.films import FilmListView, FilmDetailView

urlpatterns = [
    path('', FilmListView.as_view(), name='film-list'),
    path('<slug:slug>', FilmDetailView.as_view(), name='film-detail'),
    path('<slug:slug>/about', films.about, name='film-about'),
    path('<slug:slug>/gallery', films.gallery, name='film-gallery'),
    path('<slug:slug>/weeklies', films.weeklies, name='film-weeklies'),
]
