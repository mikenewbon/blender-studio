"""Commonly used template tags and filters."""
from typing import Dict, Any
import logging

from django import template
from django.contrib.auth import get_user_model
from django.template.defaultfilters import stringfilter
from django.utils.html import mark_safe

from common import queries
from common.markdown import (
    render as render_markdown,
    render_unsafe as render_markdown_unsafe,
    render_as_text as render_markdown_as_text,
)
from characters.queries import get_published_characters
from common.queries import get_latest_trainings_and_production_lessons
from common.shortcodes import render
from films.models import Film
from markupsafe import Markup

User = get_user_model()
register = template.Library()
logger = logging.getLogger(__name__)


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


@register.filter(name='unmarkdown')
def unmarkdown(text: str) -> str:
    """Remove markdown from markdown, leave text."""
    try:
        return render_markdown_as_text(text)
    except Exception:
        logger.exception('Failed to render markdown "as text"')
        return text


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


@register.filter(name='add_form_classes')
def add_form_classes(form, size_class=""):
    """Add Bootstrap classes and our custom classes to the form fields."""
    for field_name, field in form.fields.items():
        input_type = getattr(field.widget, 'input_type', None)
        if input_type in ('radio', 'checkbox'):
            continue
        classes = {'form-control'}
        if size_class:
            classes.add(f'form-control-{size_class}')
        if input_type == 'select':
            classes.add('form-select')
            if size_class:
                classes.add(f'form-select-{size_class}')
        field.widget.attrs.update({'class': ' '.join(classes)})

    # Add error class to all the fields with errors
    invalid_fields = form.fields if '__all__' in form.errors else form.errors
    for field_name in invalid_fields:
        attrs = form.fields[field_name].widget.attrs
        attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
    return form


@register.simple_tag()
def get_featured() -> Dict[str, Any]:
    """Return featured content: trainings and films."""
    return {
        'films': Film.objects.filter(is_featured=True),
        'trainings': get_latest_trainings_and_production_lessons(),
        'characters': get_published_characters(),
    }


@register.simple_tag(takes_context=True)
def get_video_progress_seconds(context, video):
    """Return video progress for currently logged in user."""
    if not video:
        return None
    request = context.get('request')
    if request.user.is_anonymous:
        return None
    progress_position = video.get_progress_position(request.user.pk)
    return progress_position.total_seconds() if progress_position else None
