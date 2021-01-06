"""Commonly used decorators."""
from functools import wraps
from typing import Any, Callable

from django.http import HttpResponseForbidden, HttpResponse
from django.http.request import HttpRequest

from common.queries import has_active_subscription


def subscription_required(function: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Return HTTP Forbidden if requests user doesn't have active subscription."""

    @wraps(function)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not has_active_subscription(request.user):
            return HttpResponseForbidden('An active subscription is required')

        return function(request, *args, **kwargs)

    return wrapper
