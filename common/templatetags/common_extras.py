"""Commonly used template tags and filters."""
from django import template
from django.contrib.auth.models import User
from django.utils.html import mark_safe

from common.shortcodes import render
from common import queries

register = template.Library()


@register.simple_tag(takes_context=True)
def with_shortcodes(context, text: str) -> str:
    """Transform shortcodes in a given text into their HTML snippets."""
    return mark_safe(render(text, context))


@register.filter(name='has_group')
def has_group(user: User, group_name: str) -> bool:
    """Check if a given user is in a given group.

    E.g. can be used to check subscription status in templates:

    {% load common_extras %}
    {% if request.user|has_group:"subscriber" %}{% endif %}
    """
    return queries.has_group(user, group_name)
