from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.models import chapters, trainings
from training_main.types import TypeSafeTemplateResponse


def training(
    request: HttpRequest, *, training: trainings.Training, chapters: Sequence[chapters.Chapter]
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/trainings/training.html',
            context={'training': training, 'chapters': chapters},
        )
    )
