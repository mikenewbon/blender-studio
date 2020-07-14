from django.contrib.auth.models import User
from django.db import models
from django.urls.base import reverse

from common import mixins


class Comment(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        permissions = [('moderate_comment', 'Can moderate comments')]

    # Whenever a User is deleted their Comment lives on to ensure integrity of the conversation.
    # Instead, we remove the reference to the User to honor the deletion request as much as
    # possible.
    user = models.ForeignKey(
        User, null=True, blank=False, on_delete=models.SET_NULL, related_name='comments',
    )

    # If a comment has replies we prevent it from being deleted to ensure integrity of the
    # conversation.
    reply_to = models.ForeignKey(
        'Comment',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT,
        related_name='replies',
    )

    message = models.TextField()

    likes = models.ManyToManyField(User, through='Like', related_name='liked_comments')

    def __str__(self) -> str:
        return f'Comment by {self.username} @ {self.date_updated}'

    @property
    def username(self) -> str:
        return '<deleted>' if self.user is None else self.user.username

    @property
    def like_url(self) -> str:
        return reverse('comment_like', kwargs={'comment_pk': self.pk})

    @property
    def edit_url(self) -> str:
        return reverse('comment_edit', kwargs={'comment_pk': self.pk})

    @property
    def delete_url(self) -> str:
        return reverse('comment_delete', kwargs={'comment_pk': self.pk})


class Like(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'comment'], name='only_one_like_per_comment_and_user'
            )
        ]

    # Whenever a User is deleted their Like lives on to ensure integrity of the conversation.
    # Instead, we remove the reference to the User to honor the deletion request as much as
    # possible.
    user = models.ForeignKey(User, null=True, blank=False, on_delete=models.SET_NULL)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'Like by {self.username} on Comment {self.comment.id}'

    @property
    def username(self) -> str:
        return '<deleted>' if self.user is None else self.user.username
