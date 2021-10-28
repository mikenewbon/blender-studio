from typing import Optional

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from comments.typed_templates import Comments
from common.typed_templates.types import TypeSafeTemplateResponse
from training.typed_templates.types import (
    Chapter,
    Navigation,
    Training,
    Video,
)
from training.models.sections import Section


def section(
    request: HttpRequest,
    *,
    training: Training,
    chapter: Chapter,
    section: Section,
    video: Optional[Video],
    comments: Comments,
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
                'navigation': navigation,
            },
        )
    )
