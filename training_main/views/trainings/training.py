from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from training_main import responses, queries
from training_main.responses.types import TypeSafeTemplateResponse
from training_main.views.common import (
    training_model_to_template_type,
    chapter_model_to_template_type,
)
from training_main.views.decorators import login_required


@require_safe
@login_required
def training(request: HttpRequest, *, training_slug: str) -> TypeSafeTemplateResponse:
    result = queries.trainings.from_slug_with_chapters(
        user_pk=request.user.pk, training_slug=training_slug
    )

    if result is None:
        return responses.errors.not_found(request)
    else:
        training, favorited, chapters = result
        return responses.trainings.training.training(
            request,
            training=training_model_to_template_type(training, favorited),
            chapters=[chapter_model_to_template_type(chapter) for chapter in chapters],
        )
