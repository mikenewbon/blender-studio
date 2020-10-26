"""Handle cleaning and rendering of markdown."""
from typing import Optional
import re

from markupsafe import Markup
import bleach
import mistune

_markdown: Optional[mistune.Markdown] = None


def sanitize(text: str) -> str:
    """Remove **all** HTML tags from a given text."""
    return bleach.clean(text)


class ShortcodeLinkLinkInlineLexer(mistune.InlineLexer):
    """Allows shortcodes with links to skip urlise/linkify."""

    def enable_shortcode_link(self):
        """Find lines that feature '{attachment link=' or '{iframe src=' intact."""
        lexer_regexp = r'{(?:attachment\s+|iframe\s+)\w*(?:\s*link|\s*src)=.*'
        self.rules.shortcode_link = re.compile(lexer_regexp)
        # Place the rule towards the top
        self.default_rules.insert(1, 'shortcode_link')

    def output_shortcode_link(self, m):
        """Leave found lexem intact."""
        return m.string


markdown_inline_lexer = ShortcodeLinkLinkInlineLexer(mistune.Renderer())
markdown_inline_lexer.enable_shortcode_link()


def render(text: str) -> Markup:
    """Render given text as markdown."""
    global _markdown

    if _markdown is None:
        _markdown = mistune.Markdown(escape=True, inline=markdown_inline_lexer)

    return Markup(_markdown(text))
