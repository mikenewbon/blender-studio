from typing import TypeVar, Callable, cast

from django.contrib.auth.decorators import login_required as django_login_required
from django.http.response import HttpResponseBase

F = TypeVar('F', bound=Callable[..., HttpResponseBase])


def login_required(function: F) -> F:
    """We redefine this decorator for type safety."""
    return cast(F, django_login_required(function))
