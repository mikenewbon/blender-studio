from typing import Optional, List

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.models import chapters, sections, trainings
from training_main.types import TypeSafeTemplateResponse


def section(
    request: HttpRequest,
    *,
    training: trainings.Training,
    chapter: chapters.Chapter,
    section: sections.Section,
    video: Optional[sections.Video],
    assets: List[sections.Asset],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training_main/trainings/chapters/sections/section.html',
            context={
                'training': training,
                'chapter': chapter,
                'section': section,
                'video': video,
                'assets': assets,
            },
        )
    )
