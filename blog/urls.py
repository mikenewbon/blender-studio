from django.urls import path

from blog.views.api.comment import comment
from blog.views.blog import PostList, PostDetail

urlpatterns = [
    path('api/posts/<int:post_pk>/comment', comment, name='api-post-comment'),
    path('', PostList.as_view(), name='post-list'),
    path('<slug:slug>', PostDetail.as_view(), name='post-detail'),
]
