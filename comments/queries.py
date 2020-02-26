from comments import models


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


def moderator_edit_comment(*, comment_pk: int, user_pk: int, message: str) -> models.Comment:
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
