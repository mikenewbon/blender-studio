from __future__ import annotations

from typing import NewType

from django.http import JsonResponse
from django.template.response import TemplateResponse

TypeSafeTemplateResponse = NewType('TypeSafeTemplateResponse', TemplateResponse)
TypeSafeJsonResponse = NewType('TypeSafeJsonResponse', JsonResponse)
