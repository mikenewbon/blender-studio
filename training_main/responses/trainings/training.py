from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses import types
from training_main.types import TypeSafeTemplateResponse


def training(
    request: HttpRequest, *, training: types.Training, chapters: Sequence[types.Chapter]
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/trainings/training.html',
            context={'training': training, 'chapters': chapters},
        )
    )
