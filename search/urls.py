from django.urls.conf import path

from search.views import search

urlpatterns = [
    path('', search, name='search'),
]
