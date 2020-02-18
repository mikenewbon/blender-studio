from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses import types
from training_main.types import TypeSafeTemplateResponse


def chapter(
    request: HttpRequest,
    *,
    training: types.Training,
    chapter: types.Chapter,
    sections: Sequence[types.Section],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/trainings/chapters/chapter.html',
            context={'training': training, 'chapter': chapter, 'sections': sections},
        )
    )
