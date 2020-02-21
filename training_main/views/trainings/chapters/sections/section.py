from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from training_main import responses, queries
from training_main.responses.types import TypeSafeTemplateResponse
from training_main.views.common import (
    training_model_to_template_type,
    chapter_model_to_template_type,
    section_model_to_template_type,
    video_model_to_template_type,
    asset_model_to_template_type,
    comments_to_template_type,
)
from training_main.views.decorators import login_required


@require_safe
@login_required
def section(
    request: HttpRequest,
    *,
    training_slug: str,
    chapter_index: int,
    chapter_slug: str,
    section_index: int,
    section_slug: str,
) -> TypeSafeTemplateResponse:
    result = queries.sections.from_slug(user_pk=request.user.pk, section_slug=section_slug)

    if result is None:
        return responses.errors.not_found(request)
    else:
        training, training_favorited, chapter, section, maybe_video, assets, comments = result

        if maybe_video is None:
            video = None
        else:
            video_model, video_start_position = maybe_video
            video = video_model_to_template_type(
                video=video_model, start_position=video_start_position
            )

        return responses.trainings.chapters.sections.section.section(
            request,
            training=training_model_to_template_type(training, training_favorited),
            chapter=chapter_model_to_template_type(chapter),
            section=section_model_to_template_type(section),
            video=video,
            assets=[asset_model_to_template_type(asset) for asset in assets],
            comments=comments_to_template_type(comments, section.comment_url),
        )
