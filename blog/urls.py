from django.urls import path, include

from blog.views.api.comment import comment
from blog.views.api.like import post_like
from blog.views.blog import PostList, PostDetail

urlpatterns = [
    path(
        'api/posts/<int:post_pk>/',
        include(
            [
                path('comment/', comment, name='api-post-comment'),
                path('like/', post_like, name='api-post-like'),
            ]
        ),
    ),
    path('', PostList.as_view(), name='post-list'),
    path('<slug:slug>/', PostDetail.as_view(), name='post-detail'),
]
