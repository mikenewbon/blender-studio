from django.urls.conf import path

from stats.views import index

urlpatterns = [
    path('', index, name='stats-index'),
]
