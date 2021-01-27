"""Commonly used template tags and filters."""
from django import template
from django.contrib.auth import get_user_model
from django.template.defaultfilters import stringfilter
from django.utils.html import mark_safe

from common import queries
from common.markdown import (
    render as render_markdown,
    render_unsafe as render_markdown_unsafe,
)
from common.shortcodes import render
from markupsafe import Markup

User = get_user_model()
register = template.Library()


class CaptureNode(template.Node):
    """Implement custom template node for {% capture %} tag."""

    def __init__(self, nodelist, varname):  # noqa: D107
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):  # noqa: D102
        output = self.nodelist.render(context)
        context[self.varname] = output
        return ''


@register.tag(name='capture')
def do_capture(parser, token):
    """Implement a custom tag for assigning short template snippets to variables.

    {% capture y %}{% if x %}{{ a }}{% else %}{{ b }}{% endif %}{% endcapture %}
    """
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("'capture' node requires a variable name.")
    nodelist = parser.parse(('endcapture',))
    parser.delete_first_token()
    return CaptureNode(nodelist, args)


@register.simple_tag(takes_context=True)
def with_shortcodes(context, text: str) -> str:
    """Transform shortcodes in a given text into their HTML snippets."""
    return mark_safe(render(text, context))


@register.filter(name='markdown')
def markdown(text: str) -> Markup:
    """Render markdown."""
    return render_markdown(text)


@register.filter(name='markdown_unsafe')
def markdown_unsafe(text: str) -> Markup:
    """Render unsafe markdown with HTML tags."""
    return render_markdown_unsafe(text)


@register.filter(name='has_group')
def has_group(user: User, group_name: str) -> bool:
    """Check if a given user is in a given group."""
    return queries.has_group(user, group_name)


@register.filter(name='has_active_subscription')
def has_active_subscription(user: User) -> bool:
    """Check subscription status of the given user."""
    return queries.has_active_subscription(user)


@register.simple_tag(takes_context=True)
def absolute_url(context, path: str) -> str:
    """Return an absolute URL of a given path."""
    request = context.get('request')
    if not request:
        return ''
    return request.build_absolute_uri(path)


@register.filter(is_safe=False)
@stringfilter
def endswith(value: str, suffix: str) -> bool:
    """Check if a string ends with a given suffix."""
    return value.endswith(suffix)
