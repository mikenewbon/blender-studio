from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from common.typed_templates.types import TypeSafeTemplateResponse
from training.typed_templates.types import Training, Chapter, Section


def chapter(
    request: HttpRequest, *, training: Training, chapter: Chapter, sections: Sequence[Section],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training/chapter.html',
            context={'training': training, 'chapter': chapter, 'sections': sections},
        )
    )
