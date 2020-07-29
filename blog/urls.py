from django.urls import path

from blog.views.blog import post_list, post_detail

urlpatterns = [
    path('', post_list, name='post-list'),
    path('<slug:post_slug>', post_detail, name='post-detail'),
]
