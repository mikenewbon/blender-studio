from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from comments.views.common import comments_to_template_type
from common.typed_templates.errors import not_found
from common.typed_templates.types import TypeSafeTemplateResponse
from subscriptions.decorators import subscription_required
from training import queries, typed_templates
from training.models.progress import UserSectionProgress
from training.typed_templates.types import SectionProgressReportingData
from training.views.common import (
    asset_model_to_template_type,
    chapter_model_to_template_type,
    navigation_to_template_type,
    section_model_to_template_type,
    training_model_to_template_type,
    video_model_to_template_type,
)


@require_safe
@login_required
@subscription_required
def section(
    request: HttpRequest,
    *,
    training_slug: str,
    chapter_index: int,
    chapter_slug: str,
    section_index: int,
    section_slug: str,
) -> TypeSafeTemplateResponse:
    result = queries.sections.from_slug(
        user_pk=request.user.pk,
        training_slug=training_slug,
        chapter_slug=chapter_slug,
        section_slug=section_slug,
    )

    if result is None:
        return not_found(request)
    else:
        training, training_favorited, chapter, section, maybe_video, assets, comments = result

        if maybe_video is None:
            video = None
        else:
            video_model, video_start_position = maybe_video
            video = video_model_to_template_type(
                video=video_model, start_position=video_start_position
            )

        navigation = queries.trainings.navigation(user_pk=request.user.pk, training_pk=training.pk)

        return typed_templates.section.section(
            request,
            training=training_model_to_template_type(training, training_favorited),
            chapter=chapter_model_to_template_type(chapter),
            section=section_model_to_template_type(section),
            video=video,
            assets=[asset_model_to_template_type(asset) for asset in assets],
            comments=comments_to_template_type(
                comments,
                section.comment_url,
                user_is_moderator=request.user.has_perm('training.moderate_comment'),
            ),
            section_progress_reporting_data=SectionProgressReportingData(
                progress_url=section.progress_url,
                started_timeout=UserSectionProgress.started_duration_pageview_duration.total_seconds(),
                finished_timeout=(
                    UserSectionProgress.finished_duration_pageview_duration.total_seconds()
                    if video is None
                    else None
                ),
            ),
            navigation=navigation_to_template_type(*navigation, user=request.user, current=section),
        )
