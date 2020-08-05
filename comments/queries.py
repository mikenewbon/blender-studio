import logging
from typing import List

from django.db.models import Model, Exists, OuterRef, Case, Value, When, Count, QuerySet
from django.db.models.fields import BooleanField

from comments import models
from comments.models import Comment, Like


log = logging.getLogger(__name__)


def get_annotated_comments(obj: Model, user_pk: int) -> List[Comment]:
    """Returns a list of annotated comments associated with the model instance `obj`.

    Args:
        obj: a model instance with comments under the attribute 'comments';
        user_pk: an int, the pk of the currently logged-in user.

    Returns:
        A queryset of comments associated with the `obj`.
        Comments without replies which have been marked as deleted are excluded.
        Annotations are used in the objects passed to the template:
        - liked: bool; whether the current user (given by user_pk argument) likes a comment;
        - number_of_likes: int; the number of likes associated with a comment;
        - owned_by_current_user: bool.
    """
    comments: 'QuerySet[Comment]' = getattr(obj, 'comments')

    return list(
        comments.exclude(date_deleted__isnull=False, replies__isnull=True)
        .prefetch_related('user', 'reply_to')
        .annotate(
            liked=Exists(Like.objects.filter(comment_id=OuterRef('pk'), user_id=user_pk)),
            number_of_likes=Count('likes'),
            owned_by_current_user=Case(
                When(user_id=user_pk, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        .all()
    )


def set_comment_like(*, comment_pk: int, user_pk: int, like: bool) -> int:
    if like:
        models.Like.objects.update_or_create(
            comment_id=comment_pk, user_id=user_pk,
        )
    else:
        models.Like.objects.filter(comment_id=comment_pk, user_id=user_pk).delete()

    return models.Like.objects.filter(comment_id=comment_pk).count()


def edit_comment(*, comment_pk: int, user_pk: int, message: str) -> models.Comment:
    comment: models.Comment = models.Comment.objects.get(id=comment_pk, user_id=user_pk)
    comment.message = message
    comment.save()
    return comment


def moderator_edit_comment(*, comment_pk: int, message: str) -> models.Comment:
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    comment.message = message
    comment.save()
    return comment


def delete_comment(*, comment_pk: int, user_pk: int) -> None:
    """Soft-delete the comment, i.e. mark is as deleted."""
    comment: models.Comment = models.Comment.objects.get(id=comment_pk, user_id=user_pk)
    if comment.is_deleted:
        log.warning(f'User {user_pk} has tried to delete a deleted comment with id={comment_pk}.')
        return
    comment.soft_delete()


def moderator_delete_comment(*, comment_pk: int) -> None:
    """Soft-delete the comment, i.e. mark is as deleted."""
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    if comment.is_deleted:
        log.warning(f'A moderator has tried to delete a deleted comment with id={comment_pk}.')
        return
    comment.soft_delete()


def archive_comment(*, comment_pk: int) -> bool:
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    is_archived = comment.archive_tree()
    return is_archived


def delete_comment_tree(*, comment_pk: int) -> None:
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    comment.soft_delete_tree()
