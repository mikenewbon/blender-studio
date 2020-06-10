from django.urls import path

from films.views import films, gallery

urlpatterns = [
    path('', films.FilmListView.as_view(), name='film-list'),
    path('<slug:film_slug>', films.FilmDetailView.as_view(), name='film-detail'),
    path('<slug:film_slug>/about', films.about, name='film-about'),
    path('<slug:film_slug>/gallery', gallery.collection_list, name='film-gallery'),
    path('<slug:film_slug>/weeklies', films.weeklies, name='film-weeklies'),
    path(
        '<slug:film_slug>/<slug:collection_slug>',
        gallery.collection_detail,
        name='collection-detail',
    ),
]
