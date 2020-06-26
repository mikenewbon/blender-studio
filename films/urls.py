from django.urls import path

from films.views import films, gallery, weeklies
from films.views.api.assets import asset as api_asset, asset_zoom
urlpatterns = [
    path('api/assets/<int:asset_pk>', api_asset, name='api-asset'),
    path('api/assets/<int:asset_pk>/zoom', asset_zoom, name='api-asset-zoom'),
    path('', films.FilmListView.as_view(), name='film-list'),
    path('<slug:film_slug>', films.film_detail, name='film-detail'),
    path('<slug:film_slug>/about', films.about, name='film-about'),
    path('<slug:film_slug>/gallery', gallery.collection_list, name='film-gallery'),
    path('<slug:film_slug>/weeklies', weeklies.production_log_list, name='film-weeklies'),
    path('<slug:film_slug>/assets/<slug:asset_slug>', gallery.asset_detail, name='asset-detail'),
    path(
        '<slug:film_slug>/<slug:collection_slug>',
        gallery.collection_detail,
        name='collection-detail',
    ),
]
