import logging

import blog.models as models


log = logging.getLogger(__name__)


def set_post_like(*, post_pk: int, user_pk: int, like: bool) -> int:
    """Like or unlike a blog post."""
    if like:
        models.Like.objects.update_or_create(post_id=post_pk, user_id=user_pk)
    else:
        models.Like.objects.filter(post_id=post_pk, user_id=user_pk).delete()

    return models.Like.objects.filter(post_id=post_pk).count()
