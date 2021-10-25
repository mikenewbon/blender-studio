"""Implements blog post comments API."""
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from blog.models import PostComment
from comments.views.common import comment_response
from common.decorators import subscription_required


@require_POST
@login_required
@subscription_required
def comment(request: HttpRequest, *, post_pk: int) -> JsonResponse:
    """Add a top-level comment under a blog post or a reply to another comment."""
    return comment_response(request, PostComment, 'post_id', post_pk)
