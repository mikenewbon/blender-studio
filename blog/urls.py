from django.urls import path

from blog.views.api.comment import comment
from blog.views.blog import post_list, post_detail

urlpatterns = [
    path('api/posts/<int:post_pk>/comment', comment, name='api-post-comment'),
    path('', post_list, name='post-list'),
    path('<slug:post_slug>', post_detail, name='post-detail'),
]
