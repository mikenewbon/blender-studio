from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from training_main import queries
from training_main import responses
from training_main.responses.home import RecentlyWatchedSection
from training_main.responses.types import TypeSafeTemplateResponse
from training_main.views.common import training_model_to_template_type
from training_main.views.decorators import login_required


@require_safe
def home(request: HttpRequest) -> TypeSafeTemplateResponse:
    if request.user.is_authenticated:
        return home_authenticated(request)
    else:
        return home_not_authenticated(request)


@login_required
def home_authenticated(request: HttpRequest) -> TypeSafeTemplateResponse:
    favorited_trainings = queries.trainings.favorited(user_pk=request.user.pk)
    recently_watched_sections = queries.sections.recently_watched(user_pk=request.user.pk)
    all_trainings = queries.trainings.all(user_pk=request.user.pk)

    return responses.home.home_authenticated(
        request,
        recently_watched_sections=[
            RecentlyWatchedSection(
                index=section.index,
                name=section.name,
                text=section.text,
                url=section.url,
                training_name=getattr(section, 'training_name'),
                chapter_index=getattr(section, 'chapter_index'),
                chapter_name=getattr(section, 'chapter_name'),
                progress_fraction=(
                    0.5
                    if getattr(section, 'video_position') is None
                    or getattr(section, 'video_duration') is None
                    else getattr(section, 'video_position') / getattr(section, 'video_duration')
                ),
            )
            for section in recently_watched_sections
        ],
        favorited_trainings=[
            training_model_to_template_type(training, favorited=True)
            for training in favorited_trainings
        ],
        all_trainings=[
            training_model_to_template_type(training, favorited=training in favorited_trainings)
            for training in all_trainings
        ],
    )


def home_not_authenticated(request: HttpRequest,) -> TypeSafeTemplateResponse:
    all_trainings = queries.trainings.all(user_pk=None)
    return responses.home.home_not_authenticated(
        request,
        all_trainings=[
            training_model_to_template_type(training, favorited=False) for training in all_trainings
        ],
    )
