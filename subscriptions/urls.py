import looper.urls
from django.urls import include, path

urlpatterns = [path('', include(looper.urls))]
