from typing import Dict

from django import template

register = template.Library()


@register.inclusion_tag('comments/components/comment_input.html')
def comment_input(profile_image_url: str, button_label: str, div_class: str) -> Dict:
    """
    Creates a comment input form.

    **Tag template:**
    :template:`comments/components/comment_input.html`
    """
    return {
        'profile_image_url': profile_image_url,
        'button_label': button_label,
        'div_class': div_class,
    }
