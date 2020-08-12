from django.urls.conf import path

from search.views import search, api_search, api_search_sort

urlpatterns = [
    path('api/search', api_search, name='api-search'),
    path('api/sort/<str:sorting_param>', api_search_sort, name='api-search-sort'),
    path('', search, name='search'),
]
