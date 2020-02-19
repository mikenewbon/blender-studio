from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses.common import Training, Chapter, Section
from training_main.responses.types import TypeSafeTemplateResponse


def chapter(
    request: HttpRequest, *, training: Training, chapter: Chapter, sections: Sequence[Section],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/trainings/chapters/chapter.html',
            context={'training': training, 'chapter': chapter, 'sections': sections},
        )
    )
