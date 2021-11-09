"""Custom markdown renderers."""
from mistune.renderers import BaseRenderer


class TextRenderer(BaseRenderer):  # noqa: D102
    """Turn markdown from plain text into even planer text."""

    NAME = 'text'
    IS_TREE = False

    def text(self, text):  # noqa: D102
        return text

    def heading(self, text, level):  # noqa: D102
        return text.strip() + '\n'

    def list(self, text, ordered, level, start=None):  # noqa: D102
        return text

    def list_item(self, text, level):  # noqa: D102
        return ' ' * (level - 1) + '- ' + text + '\n'

    def block_text(self, text):  # noqa: D102
        return text

    def thematic_break(self):  # noqa: D102
        return '\n---\n\n'

    def paragraph(self, text):  # noqa: D102
        return text.strip('\n') + '\n\n'

    def link(self, link, text=None, title=None):  # noqa: D102
        return '{text}: {link}'.format(text=text, link=link)

    def block_quote(self, text):  # noqa: D102
        return '\n'.join(['> ' + line for line in text.strip().splitlines()]) + '\n'

    def newline(self):  # noqa: D102
        return '\n'

    def block_code(self, code, info=None):  # noqa: D102
        return '\n' + code.strip('\n') + "\n\n"

    def block_html(self, value, **kwargs):  # noqa: D102
        from common.markdown import sanitize

        return sanitize(value)

    def codespan(self, text):  # noqa: D102
        return '`{text}`'.format(text=text)

    def strong(self, text):  # noqa: D102
        return '**' + text + '**'

    def linebreak(self):  # noqa: D102
        return '\n'

    def table(self, text):  # noqa: D102
        return text

    def emphasis(self, text):  # noqa: D102
        return text
