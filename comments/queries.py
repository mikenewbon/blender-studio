from typing import List

from django.db.models import Model, Exists, OuterRef, Case, Value, When, Count
from django.db.models.fields import BooleanField

from comments import models
from comments.models import Comment, Like


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
    assert hasattr(
        obj, 'comments'
    ), f'Object of type {type(obj)} does not have a "comments" attribute.'

    return list(
        obj.comments.exclude(date_deleted__isnull=False, replies__isnull=True)
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
    comment: models.Comment = models.Comment.objects.get(id=comment_pk, user_id=user_pk)
    comment.delete()


def moderator_delete_comment(*, comment_pk: int) -> None:
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    comment.delete()


def moderator_archive_comment(*, comment_pk: int) -> bool:
    comment: models.Comment = models.Comment.objects.get(id=comment_pk)
    comment.is_archived = not comment.is_archived
    comment.save()
    return comment.is_archived
