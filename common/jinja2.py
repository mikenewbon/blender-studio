from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment
from sorl.thumbnail import get_thumbnail


def environment(**options):
    env = Environment(**options)
    env.globals.update({'static': static, 'url': reverse, 'thumbnail': get_thumbnail})
    return env
