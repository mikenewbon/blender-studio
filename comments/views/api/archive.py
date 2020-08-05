from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from comments.queries import archive_comment


@require_POST
@login_required
def comment_archive_tree(request: HttpRequest, *, comment_pk: int) -> JsonResponse:
    if request.user.has_perm('comments.moderate_comment'):
        is_archived = archive_comment(comment_pk=comment_pk)

        return JsonResponse({'comment_pk': comment_pk, 'is_archived': is_archived})

    return JsonResponse({}, status=403, reason='User does not have comment moderation permission.')
