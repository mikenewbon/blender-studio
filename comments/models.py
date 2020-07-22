from typing import Any, Tuple, Dict

from django.contrib.auth.models import User
from django.db import models
from django.urls.base import reverse
from django.utils import timezone

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
    # conversation (see the `delete` method below).
    reply_to = models.ForeignKey(
        'Comment',
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT,
        related_name='replies',
    )
    message = models.TextField(null=True)
    date_deleted = models.DateTimeField(null=True, editable=False)
    # This flag adds a possibility to mark a comment as 'resolved' or 'outdated'.
    is_archived = models.BooleanField(default=False)

    likes = models.ManyToManyField(User, through='Like', related_name='liked_comments')

    def __str__(self) -> str:
        return f'Comment by {self.username} @ {self.date_updated}'

    @property
    def username(self) -> str:
        return '<deleted>' if self.user is None else self.user.username

    @property
    def full_name(self) -> str:
        return '<deleted>' if self.user is None else self.user.get_full_name()

    @property
    def is_deleted(self) -> bool:
        """Check if a comment with replies has been deleted."""
        return self.date_deleted is not None

    @property
    def like_url(self) -> str:
        return reverse('comment_like', kwargs={'comment_pk': self.pk})

    @property
    def edit_url(self) -> str:
        return reverse('comment_edit', kwargs={'comment_pk': self.pk})

    @property
    def delete_url(self) -> str:
        return reverse('comment_delete', kwargs={'comment_pk': self.pk})

    def delete(self, using: Any = None, keep_parents: bool = False) -> Tuple[int, Dict[str, int]]:
        """
        Instead of deleting a comment, only mark it as deleted.

        To preserve the integrity of the conversation, completely deleting comments
        is not allowed. However, we should allow users to remove their comments from
        the website somehow. To achieve this, we set the `date_deleted` attribute to
        mark them as deleted (this can be checked with the `is_deleted` property).
        """
        self.date_deleted = timezone.now()
        self.save()
        return 0, {self._meta.label: 0}


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
