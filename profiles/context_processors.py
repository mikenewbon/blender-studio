"""Add additional Profile-related data into the template context."""
from typing import Dict
from dataclasses import asdict

from django.http.request import HttpRequest

from profiles.datatypes import User, Profile, Group


def user_dict(request: HttpRequest) -> Dict[str, User]:
    """Inject a JSON-serializable user into the template context."""
    user = request.user
    if user.is_authenticated:
        user_data = User(
            is_anonymous=user.is_anonymous,
            is_authenticated=user.is_authenticated,
            username=user.username,
            is_active=user.is_active,
            is_staff=user.is_staff,
            is_superuser=user.is_superuser,
            last_login=user.last_login,
            date_joined=user.date_joined,
            groups=[Group(name=group.name,) for group in user.groups.all()],
            profile=Profile(
                full_name=user.profile.full_name if getattr(user, 'profile', None) else None,
                image_url=user.profile.image_url if getattr(user, 'profile', None) else None,
            ),
        )
    else:
        user_data = User(is_anonymous=user.is_anonymous, is_authenticated=user.is_authenticated,)
    return {'user_dict': asdict(user_data)}
