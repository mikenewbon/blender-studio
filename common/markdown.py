"""Handle cleaning and rendering of markdown."""
from typing import Optional, Tuple
import re

from markupsafe import Markup
import bleach
import bleach.sanitizer
import mistune

_markdown: Optional[mistune.Markdown] = None
_markdown_with_html: Optional[mistune.Markdown] = None
SHORTCODE_WITH_LINK_PATTERN = r'{(?:attachment\s+|iframe\s+).*(?:\s*link|\s*src)=.*'
ALLOWED_TAGS_EXTRA = {
    # <a> is already allowed by bleach, but we want more allowed attributes for it
    'a': ['href', 'title', 'download', 'class'],
    'audio': ['controls'],
    'cite': ['title'],
    'figcaption': ['class'],
    'figure': ['class'],
    'footer': [],
    'img': ['alt', 'src', 'class'],
    'p': ['class'],
    'source': ['src', 'type'],
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


def parse_shortcode_link(self, match: re.Match, state) -> Tuple[str]:
    """Define how to parse a shortcode with link."""
    return 'shortcode_link', match.group()


def keep_shortcode_link(matched_text: str) -> str:
    """Leave shortcode link as is."""
    return matched_text


def plugin_shortcode_with_link(md):
    """Define a plugin that will keep shortcode links intact.

    This is necessary because by default mistune "urlises" (wraps into "a href") all links.
    """
    md.inline.register_rule('shortcode_link', SHORTCODE_WITH_LINK_PATTERN, parse_shortcode_link)
    md.inline.rules.append('shortcode_link')
    md.renderer.register('shortcode_link', keep_shortcode_link)


def render(text: str) -> Markup:
    """Render given text as markdown."""
    global _markdown

    if _markdown is None:
        _markdown = mistune.create_markdown(
            escape=True,
            plugins=[plugin_shortcode_with_link, mistune.plugins.extra.plugin_url],
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
            plugins=[plugin_shortcode_with_link, mistune.plugins.extra.plugin_url],
        )

    return Markup(_markdown_with_html(text))
