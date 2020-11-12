import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.views.decorators.http import require_POST

from comments.views.common import comment_to_json_response
from common.types import assert_cast
from training import queries


@require_POST
@login_required
def comment(request: HttpRequest, *, section_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    reply_to_pk = int(parsed_body['reply_to']) if parsed_body.get('reply_to') else None
    message = assert_cast(str, parsed_body['message'])

    comment = queries.sections.comment(
        user_pk=request.user.pk, section_pk=section_pk, message=message, reply_to_pk=reply_to_pk
    )
    return comment_to_json_response(comment)
