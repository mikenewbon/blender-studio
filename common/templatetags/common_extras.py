"""Commonly used template tags and filters."""
from django import template
from django.utils.html import mark_safe

from common.shortcodes import render

register = template.Library()


@register.simple_tag(takes_context=True)
def with_shortcodes(context, text: str) -> str:
    """Transform shortcodes in a given text into their HTML snippets."""
    return mark_safe(render(text, context))
