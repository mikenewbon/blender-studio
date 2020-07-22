from django.urls import path, include

from comments.views.api.archive import comment_archive
from comments.views.api.delete import comment_delete
from comments.views.api.edit import comment_edit
from comments.views.api.like import comment_like

urlpatterns = [
    path(
        'api/comments/<int:comment_pk>/',
        include(
            [
                path('like/', comment_like, name='comment_like'),
                path('edit/', comment_edit, name='comment_edit'),
                path('archive/', comment_archive, name='comment_archive'),
                path('delete/', comment_delete, name='comment_delete'),
            ]
        ),
    )
]
