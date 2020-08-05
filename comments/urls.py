from django.urls import path, include

from comments.views.api.archive import comment_archive_tree
from comments.views.api.delete import comment_delete, comment_delete_tree, comment_hard_delete_tree
from comments.views.api.edit import comment_edit
from comments.views.api.like import comment_like

urlpatterns = [
    path(
        'api/comments/<int:comment_pk>/',
        include(
            [
                path('like/', comment_like, name='comment-like'),
                path('edit/', comment_edit, name='comment-edit'),
                path('archive/', comment_archive_tree, name='comment-archive-tree'),
                path('delete/', comment_delete, name='comment-delete'),
                path('delete-tree/', comment_delete_tree, name='comment-delete-tree'),
                path(
                    'hard-delete-tree/', comment_hard_delete_tree, name='comment-hard-delete-tree'
                ),
            ]
        ),
    )
]
