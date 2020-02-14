from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main import responses, queries
from training_main.views.decorators import login_required


@login_required
def section(
    request: HttpRequest,
    *,
    training_slug: str,
    chapter_index: int,
    chapter_slug: str,
    section_index: int,
    section_slug: str,
) -> TemplateResponse:
    result = queries.sections.from_slug(section_slug)

    if result is None:
        return responses.errors.not_found(request)
    else:
        training, chapter, section, video, assets = result
        return responses.trainings.chapters.sections.section.section(
            request, training=training, chapter=chapter, section=section, video=video, assets=assets
        )
