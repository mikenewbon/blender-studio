import logging
from typing import List

from django.db.models import Model, Exists, OuterRef, Case, Value, When, Count, QuerySet
from django.db.models.fields import BooleanField

import comments.models as models


log = logging.getLogger(__name__)


def get_annotated_comments(obj: Model, user_pk: int) -> List[models.Comment]:
    """Return a list of annotated comments associated with the model instance `obj`.

    Args:
        obj: a model instance with comments under the attribute 'comments';
        user_pk: an int, the pk of the currently logged-in user.

    Returns:
        A queryset of comments associated with the `obj`.
        Comments which have been marked as deleted and don't have replies or only have
        deleted replies are excluded from the queryset.
        Annotations are used in the objects passed to the template:
        - liked: bool; whether the current user (given by user_pk argument) likes a comment;
        - number_of_likes: int; the number of likes associated with a comment;
        - owned_by_current_user: bool.
    """
    comments: 'QuerySet[models.Comment]' = getattr(obj, 'comments')

    return list(
        comments.exclude(date_deleted__isnull=False, replies__isnull=True)
        .exclude(date_deleted__isnull=False, replies__date_deleted__isnull=False)
        .prefetch_related('user', 'reply_to', 'like_set')
        .annotate(
            liked=Exists(models.Like.objects.filter(comment_id=OuterRef('pk'), user_id=user_pk)),
            # This excludes likes from deleted users:
            #    see https://code.djangoproject.com/ticket/15183
            # number_of_likes=Count('likes'),
            number_of_likes=Count('like__id'),
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
    """Soft-deletes the comment, i.e. marks is as deleted."""
    comment: models.Comment = models.Comment.objects.get(id=comment_pk, user_id=user_pk)
    if comment.is_deleted:
        log.warning(f'User {user_pk} has tried to delete a deleted comment with id={comment_pk}.')
        return
    comment.soft_delete()


def moderator_delete_comment(*, comment_pk: int) -> None:
    """Soft-deletes the comment, i.e. marks is as deleted."""
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    if comment.is_deleted:
        log.warning(f'A moderator has tried to delete a deleted comment with id={comment_pk}.')
        return
    comment.soft_delete()


def delete_comment_tree(*, comment_pk: int) -> None:
    """Soft-deletes (i.e. mark sas deleted) the comment and all its replies."""
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    comment.soft_delete_tree()


def hard_delete_comment_tree(*, comment_pk: int) -> None:
    """Completely deletes the comment and all its replies."""
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    comment.delete()


def archive_comment(*, comment_pk: int) -> bool:
    """Switches the `is_archived` status of all the comments in the tree.

    If the comment tree to which the comment belongs is already archived, this function
    un-archives it again.

    Args:
        comment_pk: int, the primary key (id) of a comment in the tree to be archived.

    Returns:
        is_archived: bool, the new value of the `is_archived` status of the tree's comments.
    """
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    is_archived = comment.archive_tree()
    return is_archived
