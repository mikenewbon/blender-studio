from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from common.typed_templates.types import TypeSafeTemplateResponse
from training import queries, typed_templates
from training.views.common import (
    training_model_to_template_type,
    recently_watched_sections_to_template_type,
)


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

    return typed_templates.home.home_authenticated(
        request,
        recently_watched_sections=recently_watched_sections_to_template_type(
            recently_watched_sections
        ),
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
    return typed_templates.home.home_not_authenticated(
        request,
        all_trainings=[
            training_model_to_template_type(training, favorited=False) for training in all_trainings
        ],
    )
