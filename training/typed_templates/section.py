from typing import Optional, List

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from comments.typed_templates import Comments
from common.typed_templates.types import TypeSafeTemplateResponse
from training.typed_templates.types import (
    Training,
    Chapter,
    Section,
    Video,
    Asset,
    SectionProgressReportingData,
)


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
            'training/section.html',
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
