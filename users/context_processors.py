"""Add additional User-related data into the template context."""
from typing import Dict
from dataclasses import asdict

from django.http.request import HttpRequest

from users.datatypes import User, Group


def user_dict(request: HttpRequest) -> Dict[str, User]:
    """Inject a JSON-serializable user into the template context."""
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        user_data = User(
            is_anonymous=user.is_anonymous,
            is_authenticated=user.is_authenticated,
            username=user.username,
            is_active=user.is_active,
            is_staff=user.is_staff,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            groups=[Group(name=group.name) for group in user.groups.all()],
            full_name=user.full_name,
            image_url=user.image_url,
            badges=user.badges,
        )
    else:
        user_data = User(is_anonymous=True, is_authenticated=False)
    return {'user_dict': asdict(user_data)}
