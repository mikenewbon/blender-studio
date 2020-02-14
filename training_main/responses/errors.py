from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.types import TypeSafeTemplateResponse


def not_found(request: HttpRequest) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(TemplateResponse(request, 'errors/not_found.html', status=404))
