from typing import NewType

from django.template.response import TemplateResponse

TypeSafeTemplateResponse = NewType('TypeSafeTemplateResponse', TemplateResponse)
