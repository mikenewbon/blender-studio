from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from common.typed_templates.types import TypeSafeTemplateResponse


def not_found(request: HttpRequest) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(request, 'common/errors/404.html', status=404)
    )
