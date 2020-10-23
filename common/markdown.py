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


class AttachmentLinkInlineLexer(mistune.InlineLexer):
    def enable_attachment_link(self):
        # Any line that features '{attachment <digit> link='
        self.rules.attachment_link = re.compile(r'{attachment\s\d+\slink=.*')
        # Place the rule towards the top
        self.default_rules.insert(1, 'attachment_link')

    def output_attachment_link(self, m):
        print(m.string)
        return m.string


markdown_inline_lexer = AttachmentLinkInlineLexer(mistune.Renderer())
markdown_inline_lexer.enable_attachment_link()


def render(text: str) -> Markup:
    """Render given text as markdown."""
    global _markdown

    if _markdown is None:
        _markdown = mistune.Markdown(escape=True, inline=markdown_inline_lexer)

    return Markup(_markdown(text))
