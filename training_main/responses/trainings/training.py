from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses.common import Training, Chapter
from training_main.responses.types import TypeSafeTemplateResponse


def training(
    request: HttpRequest, *, training: Training, chapters: Sequence[Chapter],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/trainings/training.html',
            context={'training': training, 'chapters': chapters},
        )
    )
