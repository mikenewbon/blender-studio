from django.urls.conf import path

from search.views import search, api_search

urlpatterns = [
    path('api/search', api_search, name='api-search'),
    path('', search, name='search'),
]
