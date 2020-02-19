from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from training_main import responses, queries
from training_main.responses.types import TypeSafeTemplateResponse
from training_main.views.common import (
    training_model_to_template_type,
    chapter_model_to_template_type,
    section_model_to_template_type,
)
from training_main.views.decorators import login_required


@require_safe
@login_required
def chapter(
    request: HttpRequest, *, training_slug: str, chapter_index: int, chapter_slug: str,
) -> TypeSafeTemplateResponse:
    result = queries.chapters.from_slug_with_sections(
        user_pk=request.user.pk, chapter_slug=chapter_slug
    )

    if result is None:
        return responses.errors.not_found(request)
    else:
        training, training_favorited, chapter, sections = result
        return responses.trainings.chapters.chapter.chapter(
            request,
            training=training_model_to_template_type(training, training_favorited),
            chapter=chapter_model_to_template_type(chapter),
            sections=[section_model_to_template_type(section) for section in sections],
        )
