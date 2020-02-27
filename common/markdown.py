from typing import Optional

import mistune
from markupsafe import Markup

_markdown: Optional[mistune.Markdown] = None


def render(text: str) -> Markup:
    global _markdown

    if _markdown is None:
        _markdown = mistune.Markdown(escape=True)

    return Markup(_markdown(text))
