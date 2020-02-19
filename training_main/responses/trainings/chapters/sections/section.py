from typing import Optional, List

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses import types
from training_main.types import TypeSafeTemplateResponse


def section(
    request: HttpRequest,
    *,
    training: types.Training,
    chapter: types.Chapter,
    section: types.Section,
    video: Optional[types.Video],
    assets: List[types.Asset],
    comments: types.Comments,
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
                'comments': comments,
            },
        )
    )
