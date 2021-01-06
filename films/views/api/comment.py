"""Comment API used in content gallery."""
import json
from typing import Optional

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from comments.models import Comment
from common.decorators import subscription_required
from common.types import assert_cast
from films.models import AssetComment


@require_POST
@login_required
@subscription_required
def comment(request: HttpRequest, *, asset_pk: int) -> JsonResponse:
    """Add a top-level comment or a reply to another comment under an asset in content gallery."""
    parsed_body = json.loads(request.body)

    reply_to_pk = int(parsed_body['reply_to']) if parsed_body.get('reply_to') else None
    message = assert_cast(str, parsed_body['message'])

    @transaction.atomic
    def create_comment(
        *, user_pk: int, asset_pk: int, message: str, reply_to_pk: Optional[int]
    ) -> Comment:
        comment = Comment.objects.create(user_id=user_pk, message=message, reply_to_id=reply_to_pk)
        AssetComment.objects.create(comment_id=comment.id, asset_id=asset_pk)
        return comment

    comment = create_comment(
        user_pk=request.user.pk, asset_pk=asset_pk, message=message, reply_to_pk=reply_to_pk
    )

    return JsonResponse(comment.to_dict())
