from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.models import chapters, sections, trainings
from training_main.types import TypeSafeTemplateResponse


def chapter(
    request: HttpRequest,
    *,
    training: trainings.Training,
    chapter: chapters.Chapter,
    sections: Sequence[sections.Section],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/trainings/chapters/chapter.html',
            context={'training': training, 'chapter': chapter, 'sections': sections},
        )
    )
