from django.urls import path

from films.views import views
from films.views.films.film import FilmListView, FilmDetailView

urlpatterns = [
    path('', FilmListView.as_view(), name='film-list'),
    path('<slug:slug>', FilmDetailView.as_view(), name='film-detail'),
    # path('', views.index, name='index'),
    path('spring', views.spring, name='spring'),
    path('coffee-run', views.coffee_run, name='coffee-run'),
    path('coffee-run/about', views.about, name='about'),
    path('coffee-run/gallery', views.gallery, name='gallery'),
    path('coffee-run/weeklies', views.weeklies, name='weeklies'),
]
