from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from common.decorators import login_required
from common.typed_templates.errors import not_found
from common.typed_templates.types import TypeSafeTemplateResponse
from training import queries, typed_templates
from training.views.common import (
    chapter_model_to_template_type,
    section_model_to_template_type,
    training_model_to_template_type,
)


@require_safe
@login_required
def chapter(
    request: HttpRequest, *, training_slug: str, chapter_index: int, chapter_slug: str,
) -> TypeSafeTemplateResponse:
    result = queries.chapters.from_slug_with_sections(
        user_pk=request.user.pk, chapter_slug=chapter_slug
    )

    if result is None:
        return not_found(request)
    else:
        training, training_favorited, chapter, sections = result
        return typed_templates.chapter.chapter(
            request,
            training=training_model_to_template_type(training, training_favorited),
            chapter=chapter_model_to_template_type(chapter),
            sections=[section_model_to_template_type(section) for section in sections],
        )
