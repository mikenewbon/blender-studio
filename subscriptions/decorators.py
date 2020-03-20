from functools import wraps
from typing import Any, Callable, TypeVar

from django.http import HttpResponseForbidden
from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from subscriptions import permissions

F = TypeVar('F', bound=Callable[..., HttpResponseBase])


def subscription_required(function: F) -> F:
    @wraps(function)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not permissions.has_subscription(request.user):
            return HttpResponseForbidden('A subscription is required to view this page')

        return function(request, *args, **kwargs)

    return wrapper
