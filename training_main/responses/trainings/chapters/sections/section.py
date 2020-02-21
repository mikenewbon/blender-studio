from typing import Optional, List

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses.common import (
    Comments,
    Asset,
    Video,
    Section,
    Chapter,
    Training,
    SectionProgressReportingData,
)
from training_main.responses.types import TypeSafeTemplateResponse


def section(
    request: HttpRequest,
    *,
    training: Training,
    chapter: Chapter,
    section: Section,
    video: Optional[Video],
    assets: List[Asset],
    comments: Comments,
    section_progress_reporting_data: SectionProgressReportingData,
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
                'section_progress_reporting_data': section_progress_reporting_data,
            },
        )
    )
