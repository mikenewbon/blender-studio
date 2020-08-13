from django.urls import path

from films.views import films, gallery, production_logs
from films.views.api.assets import asset as api_asset, asset_zoom, comment
from films.views.api.production_logs import production_logs_page

urlpatterns = [
    path('api/assets/<int:asset_pk>', api_asset, name='api-asset'),
    path('api/assets/<int:asset_pk>/zoom', asset_zoom, name='api-asset-zoom'),
    path('api/assets/<int:asset_pk>/comment', comment, name='api-asset-comment'),
    path('api/films/<int:film_pk>/logs', production_logs_page, name='api-logs-page'),
    path('', films.film_list, name='film-list'),
    path('<slug:film_slug>', films.film_detail, name='film-detail'),
    path('<slug:film_slug>/gallery', gallery.collection_list, name='film-gallery'),
    path(
        '<slug:film_slug>/production-logs',
        production_logs.production_log_list,
        name='film-production-logs',
    ),
    path('<slug:film_slug>/pages/<slug:page_slug>', films.flatpage, name='film-flatpage'),
    path(
        '<slug:film_slug>/<slug:collection_slug>',
        gallery.collection_detail,
        name='collection-detail',
    ),
]
