from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses import types
from training_main.types import TypeSafeTemplateResponse


def home_authenticated(
    request: HttpRequest,
    *,
    favorited_trainings: Sequence[types.Training],
    recently_watched_trainings: Sequence[types.Training],
    all_trainings: Sequence[types.Training],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/home_authenticated.html',
            context={
                'favorited_trainings': favorited_trainings,
                'recently_watched_trainings': recently_watched_trainings,
                'all_trainings': all_trainings,
            },
        )
    )


def home_not_authenticated(
    request: HttpRequest, *, all_trainings: Sequence[types.Training],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/home_not_authenticated.html',
            context={'all_trainings': all_trainings},
        )
    )
