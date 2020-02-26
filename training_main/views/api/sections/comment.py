import json

from django.http import JsonResponse
from django.http.request import HttpRequest
from django.views.decorators.http import require_POST

from training_main import queries
from training_main.views.common import assert_cast
from training_main.views.decorators import login_required


@require_POST
@login_required
def comment(request: HttpRequest, *, section_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    reply_to_pk = None if parsed_body['reply_to'] is None else int(parsed_body['reply_to'])
    message = assert_cast(str, parsed_body['message'])

    comment = queries.sections.comment(
        user_pk=request.user.pk, section_pk=section_pk, message=message, reply_to_pk=reply_to_pk
    )

    return JsonResponse(
        {
            'id': comment.pk,
            'username': comment.username,
            'profile_image_url': 'https://blender.chat/avatar/fsiddi',
            'date_string': comment.date_created.strftime('%d %B %Y - %H:%M'),
            'message': comment.message,
            'like_url': comment.like_url,
            'liked': False,
            'likes': 0,
            'edit_url': comment.edit_url,
            'delete_url': comment.delete_url,
        }
    )
