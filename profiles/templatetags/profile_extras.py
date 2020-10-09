"""Profile-related template tags and filters."""
from django import template
from django.contrib.auth.models import User

register = template.Library()


@register.filter(name='has_group')
def has_group(user: User, group_name: str) -> bool:
    """Check if a given user is in a given group.

    E.g. can be used to check subscription status in templates:

    {% load profile_extras %}
    {% if request.user|has_group:"subscriber" %}{% endif %}
    """
    return True if user.groups.filter(name=group_name).exists() else False
