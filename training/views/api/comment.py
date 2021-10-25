"""Comment API used in training sections."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.views.decorators.http import require_POST


from comments.views.common import comment_response
from training.models.sections import SectionComment


@require_POST
@login_required
def comment(request: HttpRequest, *, section_pk: int) -> JsonResponse:
    """Add a top-level comment or a reply to another comment under a training section."""
    return comment_response(request, SectionComment, 'section_id', section_pk)
