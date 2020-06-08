from django.urls import path

from films.views import films, gallery

urlpatterns = [
    path('', films.FilmListView.as_view(), name='film-list'),
    path('<slug:slug>', films.FilmDetailView.as_view(), name='film-detail'),
    path('<slug:slug>/about', films.about, name='film-about'),
    path('<slug:slug>/gallery', gallery.film_collection_list, name='film-gallery'),
    path('<slug:slug>/weeklies', films.weeklies, name='film-weeklies'),
]
