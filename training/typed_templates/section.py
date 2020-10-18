from typing import List, Optional

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from comments.typed_templates import Comments
from common.typed_templates.types import TypeSafeTemplateResponse
from training.typed_templates.types import (
    StaticAsset,
    Chapter,
    Navigation,
    Section,
    SectionProgressReportingData,
    Training,
    Video,
)


def section(
    request: HttpRequest,
    *,
    training: Training,
    chapter: Chapter,
    section: Section,
    video: Optional[Video],
    comments: Comments,
    section_progress_reporting_data: SectionProgressReportingData,
    navigation: Navigation,
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
                'comments': comments,
                'section_progress_reporting_data': section_progress_reporting_data,
                'navigation': navigation,
            },
        )
    )
