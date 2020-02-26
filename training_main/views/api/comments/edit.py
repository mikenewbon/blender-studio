import json

from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from training_main.queries.sections import edit_comment, moderator_edit_comment
from training_main.views.common import assert_cast
from training_main.views.decorators import login_required


@require_POST
@login_required
def comment_edit(request: HttpRequest, *, comment_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    message = assert_cast(str, parsed_body['message'])

    if request.user.has_perm('training_main.moderate_comment'):
        comment = moderator_edit_comment(
            comment_pk=comment_pk, user_pk=request.user.id, message=message
        )
    else:
        comment = edit_comment(comment_pk=comment_pk, user_pk=request.user.id, message=message)

    return JsonResponse({'message': comment.message,})
