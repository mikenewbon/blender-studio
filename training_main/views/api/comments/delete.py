from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from training_main.queries.sections import moderator_delete_comment, delete_comment
from training_main.views.decorators import login_required


@require_POST
@login_required
def comment_delete(request: HttpRequest, *, comment_pk: int) -> JsonResponse:
    if request.user.has_perm('training_main.moderate_comment'):
        moderator_delete_comment(comment_pk=comment_pk)
    else:
        delete_comment(comment_pk=comment_pk, user_pk=request.user.id)

    return JsonResponse({})
