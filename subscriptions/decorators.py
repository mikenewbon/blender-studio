from functools import wraps
from typing import Any, Callable, TypeVar, cast

from django.http import HttpResponseForbidden, HttpResponse
from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from subscriptions import permissions


def subscription_required(function: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @wraps(function)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not permissions.has_subscription(request.user):
            return HttpResponseForbidden('A subscription is required to view this page')

        return function(request, *args, **kwargs)

    return wrapper
