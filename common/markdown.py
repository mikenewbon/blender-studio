"""Handle cleaning and rendering of markdown."""
from typing import Optional, Tuple
import re

from markupsafe import Markup
import bleach
import bleach.sanitizer
import mistune

from .markdown_renderers import TextRenderer

_markdown: Optional[mistune.Markdown] = None
_markdown_with_html: Optional[mistune.Markdown] = None
_markdown_to_text: Optional[mistune.Markdown] = None
SHORTCODE_PATTERN = r'{(?:attachment|iframe|youtube|subscribe_banner)\s+[^}]*}'
ALLOWED_TAGS_EXTRA = {
    # <a> is already allowed by bleach, but we want more allowed attributes for it
    'a': ['href', 'title', 'download', 'class', 'target'],
    'audio': ['controls'],
    'caption': ['class'],
    'cite': ['title'],
    'col': ['class', 'span'],
    'colgroup': ['class', 'span'],
    'figcaption': ['class'],
    'figure': ['class'],
    'footer': [],
    'img': ['alt', 'src', 'class'],
    'p': ['class'],
    'source': ['src', 'type'],
    'table': ['class'],
    'tbody': ['class'],
    'td': ['class', 'colspan', 'headers', 'rowspan'],
    'tfoot': ['class'],
    'th': ['class', 'abbr', 'colspan', 'headers', 'rowspan', 'scope'],
    'thead': ['class'],
    'tr': ['class'],
}
ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS + list(ALLOWED_TAGS_EXTRA.keys())
ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    **ALLOWED_TAGS_EXTRA,
}


def sanitize(text: str) -> str:
    """Remove **all** HTML tags from a given text."""
    return bleach.clean(text, tags=[], attributes={}, styles=[], strip=True)


def clean(text: str) -> str:
    """Remove HTML tags that aren't whitelisted from a given text."""
    return bleach.clean(
        text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, styles=[], strip=True
    )


def parse_shortcode(self, match: re.Match, state) -> Tuple[str]:
    """Define how to parse a shortcode with link."""
    return 'shortcode', match.group()


def keep_shortcode_as_is(matched_text: str) -> str:
    """Leave shortcode link as is."""
    return matched_text


def plugin_shortcode(md):
    """Define a plugin that will keep shortcodes intact.

    This is necessary because by all links are wrapped into "a href" tag
    and double quotes are escaped in the rest of the markdown.
    """
    md.inline.register_rule('shortcode', SHORTCODE_PATTERN, parse_shortcode)
    md.inline.rules.append('shortcode')
    md.renderer.register('shortcode', keep_shortcode_as_is)


def render_as_text(text: str) -> str:
    """Turn markdown from plain text into even planer text."""
    global _markdown_to_text

    if _markdown_to_text is None:
        _markdown_to_text = mistune.Markdown(
            renderer=TextRenderer(), plugins=[mistune.PLUGINS['table']]
        )

    return _markdown_to_text(sanitize(text))


def render(text: str) -> Markup:
    """Render given text as markdown."""
    global _markdown

    if _markdown is None:
        _markdown = mistune.create_markdown(
            escape=True,
            plugins=[plugin_shortcode, mistune.plugins.extra.plugin_url, 'table'],
        )

    return Markup(_markdown(text))


def render_unsafe(text: str) -> Markup:
    """Render given text as markdown with HTML tags.

    This should only be used to render staff-edited content, e.g. blog content, but not comments.
    """
    global _markdown_with_html

    if _markdown_with_html is None:
        _markdown_with_html = mistune.create_markdown(
            # An unsafe Markdown renderer that doesn't escape remaining HTML
            escape=False,
            plugins=[plugin_shortcode, mistune.plugins.extra.plugin_url, 'table'],
        )

    return Markup(_markdown_with_html(text))
