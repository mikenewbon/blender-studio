from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from common.typed_templates.types import TypeSafeTemplateResponse
from training.typed_templates.types import Chapter, Training


def training(
    request: HttpRequest, *, training: Training, chapters: Sequence[Chapter],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request, 'training/training.html', context={'training': training, 'chapters': chapters},
        )
    )
