from django.urls import path, include

from films.views import film, gallery, production_log
from films.views.api.asset import asset as api_asset, asset_zoom, asset_like
from films.views.api.comment import comment
from films.views.api.production_log import production_logs_page

urlpatterns = [
    path(
        'api/assets/<int:asset_pk>/',
        include(
            [
                path('', api_asset, name='api-asset'),
                path('zoom/', asset_zoom, name='api-asset-zoom'),
                path('comment/', comment, name='api-asset-comment'),
                path('like/', asset_like, name='api-asset-like'),
            ]
        ),
    ),
    path('api/films/<int:film_pk>/logs', production_logs_page, name='api-logs-page'),
    path('', film.film_list, name='film-list'),
    path('<slug:film_slug>', film.film_detail, name='film-detail'),
    path('<slug:film_slug>/gallery', gallery.collection_list, name='film-gallery'),
    path(
        '<slug:film_slug>/production-logs',
        production_log.production_log_list,
        name='film-production-logs',
    ),
    path('<slug:film_slug>/pages/<slug:page_slug>', film.flatpage, name='film-flatpage'),
    path(
        '<slug:film_slug>/<slug:collection_slug>',
        gallery.collection_detail,
        name='collection-detail',
    ),
]
