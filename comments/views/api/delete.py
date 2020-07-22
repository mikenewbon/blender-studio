from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from comments.queries import delete_comment, moderator_delete_comment


@require_POST
@login_required
def comment_delete(request: HttpRequest, *, comment_pk: int) -> JsonResponse:
    if request.user.has_perm('comments.moderate_comment'):
        moderator_delete_comment(comment_pk=comment_pk)
    else:
        delete_comment(comment_pk=comment_pk, user_pk=request.user.id)

    return JsonResponse({})
