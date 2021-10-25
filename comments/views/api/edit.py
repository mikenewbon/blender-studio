"""Comment edit API."""
import json

from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from comments.models import Comment
from comments.queries import edit_comment, moderator_edit_comment
from common.types import assert_cast


@require_POST
@login_required
def comment_edit(request: HttpRequest, *, comment_pk: int) -> JsonResponse:
    """Edit a comment if permissions allow."""
    parsed_body = json.loads(request.body)

    message = assert_cast(str, parsed_body['message'])

    if request.user.has_perm('comments.moderate_comment'):
        comment = moderator_edit_comment(comment_pk=comment_pk, message=message)
    else:
        try:
            comment = edit_comment(comment_pk=comment_pk, user_pk=request.user.id, message=message)
        except Comment.DoesNotExist:
            return JsonResponse({}, status=404)

    return JsonResponse(comment.to_dict())
