from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main import responses, queries
from training_main.views.common import (
    training_model_to_template_type,
    chapter_model_to_template_type,
    section_model_to_template_type,
    video_model_to_template_type,
    asset_model_to_template_type,
    comments_to_template_type,
)
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
        training, chapter, section, video, assets, comments = result
        return responses.trainings.chapters.sections.section.section(
            request,
            training=training_model_to_template_type(training),
            chapter=chapter_model_to_template_type(chapter),
            section=section_model_to_template_type(section),
            video=None if video is None else video_model_to_template_type(video),
            assets=[asset_model_to_template_type(asset) for asset in assets],
            comments=comments_to_template_type(comments),
        )
