from typing import Dict

from django import template

register = template.Library()


@register.inclusion_tag('comments/components/comment_input.html')
def comment_input(div_class: str) -> Dict[str, str]:
    """
    Creates a comment input form.

    **Tag template:**
    :template:`comments/components/comment_input.html`
    """
    return {
        'div_class': div_class,
    }
