"""Commonly used template tags and filters."""
from django import template
from django.contrib.auth.models import User
from django.utils.html import mark_safe

from common import queries
from common.markdown import render as render_markdown
from common.shortcodes import render
from markupsafe import Markup

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


@register.filter(name='has_group')
def has_group(user: User, group_name: str) -> bool:
    """Check if a given user is in a given group.

    E.g. can be used to check subscription status in templates:

    {% load common_extras %}
    {% if request.user|has_group:"subscriber" %}{% endif %}
    """
    return queries.has_group(user, group_name)


@register.simple_tag(takes_context=True)
def absolute_url(context, path: str) -> str:
    """Return an absolute URL of a given path."""
    request = context.get('request')
    if not request:
        return ''
    return request.build_absolute_uri(path)
