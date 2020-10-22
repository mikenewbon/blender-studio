"""Handle cleaning and rendering of markdown."""
from typing import Optional

from markupsafe import Markup
import bleach
import mistune

_markdown: Optional[mistune.Markdown] = None


def sanitize(text: str) -> str:
    """Remove **all** HTML tags from a given text."""
    return bleach.clean(text)


def render(text: str) -> Markup:
    """Render given text as markdown."""
    global _markdown

    if _markdown is None:
        _markdown = mistune.Markdown(escape=True)

    return Markup(_markdown(text))
