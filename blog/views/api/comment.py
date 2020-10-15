import json
from typing import Optional

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from blog.models import PostComment
from comments.models import Comment
from common.types import assert_cast


@require_POST
@login_required
def comment(request: HttpRequest, *, post_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    reply_to_pk = None if parsed_body['reply_to'] is None else int(parsed_body['reply_to'])
    message = assert_cast(str, parsed_body['message'])

    @transaction.atomic
    def create_comment(
        *, user_pk: int, post_pk: int, message: str, reply_to_pk: Optional[int]
    ) -> Comment:
        comment = Comment.objects.create(user_id=user_pk, message=message, reply_to_id=reply_to_pk)
        PostComment.objects.create(comment_id=comment.id, post_id=post_pk)
        return comment

    comment = create_comment(
        user_pk=request.user.pk, post_pk=post_pk, message=message, reply_to_pk=reply_to_pk
    )

    return JsonResponse(
        {
            'id': comment.pk,
            'full_name': comment.full_name,
            'profile_image_url': comment.profile_image_url,
            'date_string': comment.date_created.strftime('%d %B %Y - %H:%M'),
            'message': comment.message,
            'like_url': comment.like_url,
            'liked': False,
            'likes': 0,
            'edit_url': comment.edit_url,
            'delete_url': comment.delete_url,
        }
    )
