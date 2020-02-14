from typing import TypeVar, Callable, cast

from django.contrib.auth.decorators import login_required as django_login_required
from django.template.response import TemplateResponse

F = TypeVar('F', bound=Callable[..., TemplateResponse])


def login_required(function: F) -> F:
    """We redefine this decorator for type safety."""
    return cast(F, django_login_required(function))
