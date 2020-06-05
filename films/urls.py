from django.urls import path

from films.views import views
from films.views.films.film import FilmListView, FilmDetailView

urlpatterns = [
    path('', FilmListView.as_view(), name='film-list'),
    path('<slug:slug>', FilmDetailView.as_view(), name='film-detail'),
    path('<slug:slug>/about', views.about, name='film-about'),
    path('<slug:slug>/gallery', views.gallery, name='film-gallery'),
    path('<slug:slug>/weeklies', views.weeklies, name='film-weeklies'),
]
