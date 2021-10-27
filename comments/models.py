from typing import Optional, List, Dict, Any

from actstream import action
from django.contrib.auth import get_user_model
from django.db import models
from django.urls.base import reverse
from django.utils import timezone

from common import mixins

User = get_user_model()


class Comment(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        permissions = [('moderate_comment', 'Can moderate comments')]

    # Whenever a User is deleted their Comment lives on to ensure integrity of the conversation.
    # Instead, we remove the reference to the User to honor the deletion request as much as
    # possible.
    user = models.ForeignKey(
        User, null=True, blank=False, on_delete=models.SET_NULL, related_name='comments'
    )

    # We want to enable moderators to permanently delete e.g. spam comments and their replies.
    # This should not be possible for regular users; see also the `soft_delete` method below.
    reply_to = models.ForeignKey(
        'Comment',
        null=True,
        blank=True,
        default=None,
        on_delete=models.CASCADE,
        related_name='replies',
    )
    # Markdown formatted message
    message = models.TextField(blank=True)
    # HTML rendered in the backend (on save)
    message_html = models.TextField(blank=True)
    date_deleted = models.DateTimeField(null=True, editable=False)

    # This flag adds a possibility to mark a comment as 'resolved' or 'outdated'.
    is_archived = models.BooleanField(default=False)

    # This is a temporary field used to migrate comments from the legacy cloud
    slug = models.SlugField(blank=True)

    likes = models.ManyToManyField(User, through='Like', related_name='liked_comments')

    def __str__(self) -> str:
        return f'Comment by {self.username} @ {self.date_updated:%d %B %Y %H:%M:%S}'

    @property
    def username(self) -> str:
        return '<deleted>' if self.user is None else self.user.username

    @property
    def full_name(self) -> str:
        if not self.user:
            return '<deleted>'
        return self.user.full_name

    @property
    def profile_image_url(self) -> Optional[str]:
        if not self.user:
            return None
        return self.user.image_url

    @property
    def badges(self) -> Dict:
        if not self.user:
            return None
        return self.user.badges

    @property
    def is_deleted(self) -> bool:
        """Checks if a comment with replies has been deleted."""
        return self.date_deleted is not None

    @property
    def like_url(self) -> str:
        return reverse('comment-like', kwargs={'comment_pk': self.pk})

    @property
    def edit_url(self) -> str:
        return reverse('comment-edit', kwargs={'comment_pk': self.pk})

    @property
    def archive_tree_url(self) -> str:
        return reverse('comment-archive-tree', kwargs={'comment_pk': self.pk})

    @property
    def delete_url(self) -> str:
        return reverse('comment-delete', kwargs={'comment_pk': self.pk})

    @property
    def delete_tree_url(self) -> str:
        return reverse('comment-delete-tree', kwargs={'comment_pk': self.pk})

    @property
    def hard_delete_tree_url(self) -> str:
        return reverse('comment-hard-delete-tree', kwargs={'comment_pk': self.pk})

    def soft_delete(self) -> None:
        """Instead of removing a comment, only marks it as deleted by setting its `date_deleted`.

        To preserve the integrity of the conversation, completely deleting comments
        is not allowed from the front end. However, we should allow users to remove
        their comments from the website somehow. To achieve this, we set the
        `date_deleted` attribute to mark them as deleted (this can be checked with
        the `is_deleted` property).

        This action is idempotent, as soft-deleting an already soft-deleted comment
        will not update its deletion date.
        """
        if not self.is_deleted:
            self.date_deleted = timezone.now()
            self.save()

    def soft_delete_tree(self) -> None:
        """Soft-deletes (i.e. mark as deleted) the comment and all its replies."""
        for reply in self.replies.all():
            reply.soft_delete_tree()
        self.soft_delete()

    def _get_tree_comments_pks(self) -> List[int]:
        """Returns the pks of all the comments in the `self` comment tree."""
        root = self
        while root.reply_to is not None:
            root = root.reply_to

        tree = [root]
        replies = list(root.replies.all())

        def add_replies_to_tree_comments(
            tree: List['Comment'], replies: List['Comment']
        ) -> List['Comment']:
            tree.extend(replies)
            for comment in replies:
                tree = add_replies_to_tree_comments(tree, list(comment.replies.all()))
            return tree

        tree = add_replies_to_tree_comments(tree, replies)

        return [comment.pk for comment in tree]

    def archive_tree(self) -> bool:
        """Switches the 'is_archived' status of the comment and the entire comment tree.

        It does not make sense to archive only a part of a conversation, so this action
        also affects the comment's parents and replies - the entire tree.
        """
        new_archived_status = not self.is_archived
        tree_pks = self._get_tree_comments_pks()
        Comment.objects.filter(pk__in=tree_pks).update(is_archived=new_archived_status)

        return new_archived_status

    def to_dict(self) -> Dict[str, Any]:
        """Return comment data as a dict, useful for preparing JSON API responses."""
        from common.shortcodes import render as with_shortcodes

        return {
            'id': self.pk,
            'full_name': self.full_name or self.username,
            'profile_image_url': self.profile_image_url,
            'date_string': self.date_created.strftime('%d %B %Y - %H:%M'),
            'message': self.message,
            'message_html': with_shortcodes(self.message_html),
            'like_url': self.like_url,
            'liked': False,
            'likes': self.like_set.count(),
            'edit_url': self.edit_url,
            'delete_url': self.delete_url,
        }

    def get_action_target(self):
        """Return an object this comment is relevant to, e.g. a blog post or a training section."""
        for field in ('section', 'post', 'asset', 'character_version', 'character_showcase'):
            target = getattr(self, field, None)
            if target and target.all():
                return target.first()

    def create_action(self):
        """Create an activity action from this comment.

        Used to notify users about comments in various pages, such as blog posts or film assets.
        """
        target = self.get_action_target()

        return action.send(self.user, verb='commented', action_object=self, target=target)

    @property
    def anchor(self):
        """Return an anchor for referencing the comment in a page, e.g. blog post or film asset."""
        return f'comment-{self.pk}'

    def get_absolute_url(self):
        """Return a URL to the comment within a specific page, e.g. blog post or film asset."""
        action_target = self.get_action_target()
        if action_target:
            return action_target.get_absolute_url() + f'#{self.anchor}'


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
