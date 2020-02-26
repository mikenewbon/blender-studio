from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from common.typed_templates.types import TypeSafeTemplateResponse
from training.typed_templates.types import Training, Navigation


def training(
    request: HttpRequest, *, training: Training, navigation: Navigation,
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training/training.html',
            context={'training': training, 'navigation': navigation},
        )
    )
