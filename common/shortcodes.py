"""Shortcode rendering.

Shortcodes are little snippets between curly brackets, which can be rendered
into HTML. Markdown passes such snippets unchanged to its HTML output, so this
module assumes its input is HTML-with-shortcodes.

See mulholland.xyz/docs/shortcodes/.

{iframe src='http://hey' group='subscriber' nogroup='Please subscribe to view this content'}

NOTE: nested braces fail, so something like {shortcode abc='{}'} is not
supported.

NOTE: only single-line shortcodes are supported for now, due to the need to
pass them though Markdown unscathed.

NOTE: The reason this is not implemented as a markdown plugin is that
shortcodes are often applied after markdown has been rendered and stored as HTML.
"""
import html as html_module  # I want to be able to use the name 'html' in local scope.
import logging
import re
import typing
import urllib.parse
import shortcodes
from django.template.loader import render_to_string

from common import queries
import static_assets.models as models_static_assets

_parser: shortcodes.Parser = None
_commented_parser: shortcodes.Parser = None
log = logging.getLogger(__name__)


def shortcode(name: str):
    """Class decorator for shortcodes."""

    def decorator(decorated):
        assert hasattr(decorated, '__call__'), '@shortcode should be used on callables.'
        if isinstance(decorated, type):
            as_callable = decorated()
        else:
            as_callable = decorated
        shortcodes.register(name)(as_callable)
        return decorated

    return decorator


class group_check:
    """Decorator for shortcodes.

    On call, check if the user is in a required group, otherwise,
    display a message instead of the content.

    kwargs:
        - 'group': Name of the group required for viewing.
        - 'nogroup': Optional, text shown when the user is not in the expected group.
        - others: Passed to the decorated shortcode.
    """

    def __init__(self, decorated):
        """Initialise the decorator."""
        assert hasattr(decorated, '__call__'), '@group_check should be used on callables.'
        if isinstance(decorated, type):
            as_callable = decorated()
        else:
            as_callable = decorated
        self.decorated = as_callable

    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Check user for subscription status, roles etc."""
        current_user = getattr(context.get('request'), 'user', None) if context else None
        if current_user is None:
            log.debug('Current user is not available, unable to check for groups')
        # FIXME(anna) support cap/nocap, in case there's existing content using this
        group_name = kwargs.pop('group', kwargs.pop('cap', ''))
        if group_name:
            fallback = kwargs.pop('nogroup', kwargs.pop('nocap', ''))
            if not current_user or not (
                # consider `subscriber` group a special case, and check subscription status instead
                (group_name == 'subscriber' and queries.has_active_subscription(current_user))
                or queries.has_group(current_user, group_name)
            ):
                if not fallback:
                    return ''
                html = html_module.escape(fallback)
                return f'<p class="shortcode nogroup">{html}</p>'

        return self.decorated(context, content, pargs, kwargs)


@shortcode('test')
@group_check
class Test:
    # noqa: D101
    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Just for testing.

        "{test abc='def'}" → "<dl><dt>test</dt><dt>abc</dt><dd>def</dd></dl>"
        """
        parts = ['<dl><dt>test</dt>']

        e = html_module.escape
        parts.extend([f'<dt>{e(key)}</dt><dd>{e(value)}</dd>' for key, value in kwargs.items()])
        parts.append('</dl>')
        return ''.join(parts)


@shortcode('subscribe_banner')
@group_check
class SubscribeBanner:
    # noqa: D101
    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Display a subscribe banner for anonymous and subscription-less viewers."""
        user = getattr(context.get('request'), 'user', None) if context else None
        if not user or not queries.has_active_subscription(user):
            subscribe_banner = render_to_string('blog/subscribe_jumbotron.html')
            return subscribe_banner
        return ''


@shortcode('youtube')
@group_check
class YouTube:
    # noqa: D101
    log = log.getChild('YouTube')

    def video_id(self, url: str) -> str:
        """Find the video ID from a YouTube URL.

        :raise ValueError: when the ID cannot be determined.
        """
        if re.fullmatch(r'[a-zA-Z0-9_\-]+', url):
            return url

        try:
            parts = urllib.parse.urlparse(url)
            if parts.netloc == 'youtu.be':
                return parts.path.split('/')[1]
            if parts.netloc in {'www.youtube.com', 'youtube.com'}:
                if parts.path.startswith('/embed/'):
                    return parts.path.split('/')[2]
                if parts.path.startswith('/watch'):
                    qs = urllib.parse.parse_qs(parts.query)
                    return qs['v'][0]
        except (ValueError, IndexError, KeyError):
            pass

        raise ValueError(f'Unable to parse YouTube URL {url!r}')

    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Embed a YouTube video.

        The first parameter must be the YouTube video ID or URL. The width and
        height can be passed in the equally named keyword arguments.
        """
        width = kwargs.get('width', '560')
        height = kwargs.get('height', '315')

        # Figure out the embed URL for the video.
        try:
            youtube_src = pargs[0]
        except IndexError:
            return html_module.escape('{youtube missing YouTube ID/URL}')

        try:
            youtube_id = self.video_id(youtube_src)
        except ValueError as ex:
            return html_module.escape('{youtube %s}' % "; ".join(ex.args))
        except Exception:
            return html_module.escape('{youtube missing YouTube ID/URL}')
        if not youtube_id:
            return html_module.escape('{youtube invalid YouTube ID/URL}')

        src = f'https://www.youtube.com/embed/{youtube_id}?rel=0'
        html = (
            f'<div class="embed-responsive embed-responsive-16by9">'
            f'<iframe class="shortcode youtube embed-responsive-item"'
            f' width="{width}" height="{height}" src="{src}"'
            f' frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>'
            f'</div>'
        )
        return html


@shortcode('iframe')
@group_check
def iframe(
    context: typing.Any, content: str, pargs: typing.List[str], kwargs: typing.Dict[str, str]
) -> str:
    """Show an iframe to users with from required group.

    kwargs:
        - 'group': Group required for viewing.
        - others: Turned into attributes for the iframe element.
    """
    import xml.etree.ElementTree as ET

    kwargs['class'] = f'shortcode {kwargs.get("class", "")}'.strip()
    element = ET.Element('iframe', kwargs)
    html = ET.tostring(element, encoding='unicode', method='html', short_empty_elements=True)
    return html


@shortcode('attachment')
@group_check
class Attachment:
    # noqa: D101

    def __call__(
        self,
        context: typing.Any,
        content: str,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Handle attachment shortcode."""
        try:
            slug = pargs[0]
        except KeyError:
            return '{attachment No slug given}'

        try:
            static_asset_id = int(slug)
        except ValueError:
            return '{attachment Invalid slug %s - should be a static_asset id}' % slug

        try:
            attachment = models_static_assets.StaticAsset.objects.get(pk=static_asset_id)
        except models_static_assets.StaticAsset.DoesNotExist:
            return html_module.escape('{attachment %r does not exist}' % slug)

        return self.render(attachment, pargs, kwargs)

    def render(
        self,
        static_asset: models_static_assets.StaticAsset,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ) -> str:
        """Render attachment."""
        file_renderers = {
            'image': self.render_image,
            'video': self.render_video,
        }

        renderer = file_renderers.get(static_asset.source_type, self.render_generic)
        return renderer(static_asset, pargs, kwargs)

    def render_generic(
        self,
        static_asset: models_static_assets.StaticAsset,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ):
        """Render a generic attachment."""
        return render_to_string(
            'common/components/attachments/file_generic.html', {'static_asset': static_asset}
        )

    def render_image(
        self,
        static_asset: models_static_assets.StaticAsset,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ):
        """Render an image file."""
        if 'link' in pargs:
            kwargs['link'] = 'self'
        link = None if 'link' not in kwargs else kwargs['link']
        return render_to_string(
            'common/components/attachments/file_image.html',
            {
                'static_asset': static_asset,
                'link': link,
                'class': kwargs.get('class'),
                'caption': kwargs.get('caption'),
                'zoom': kwargs.get('zoom'),
            },
        )

    def render_video(
        self,
        static_asset: models_static_assets.StaticAsset,
        pargs: typing.List[str],
        kwargs: typing.Dict[str, str],
    ):
        """Render a video file."""
        if 'link' in pargs:
            kwargs['link'] = 'self'
        link = None if 'link' not in kwargs else kwargs['link']
        # TODO(fsiddi) Handle processing video
        is_processing = False
        # TODO(fsiddi) Support looping and other options

        return render_to_string(
            'common/components/attachments/file_video.html',
            {
                'static_asset': static_asset,
                'link': link,
                'is_processing': is_processing,
                'caption': kwargs.get('caption'),
            },
        )


class SilentParser(shortcodes.Parser):
    """Silence InvalidTagError and other exceptions shortcodes.Parser raises.

    "shortcodes.Parser" raises unhandled exceptions when it meets something
    that looks like a shortcode but doesn't not have a registered handler.
    Instead, it should ignore these occurrences and keep them as-is,
    and this monkeypatches the parser to do just that.

    Ideally, this should be fixed in the "shortcodes" module, however
    latest "shortcodes==3.0.0" is not compatible with this implementation,
    and ain't nobody got time for both figuring out why and making sure it handles its exceptions.
    """

    def _parse_token(self, token, stack, *args, **kwargs):
        try:
            super()._parse_token(token, stack, *args, **kwargs)
        except Exception:
            # Just leave it as it is.
            stack[-1].children.append(shortcodes.Text(token))


def _get_parser() -> typing.Tuple[shortcodes.Parser, shortcodes.Parser]:
    """Return the shortcodes parser, create it if necessary."""
    global _parser
    if _parser is None:
        start, end = '{}'
        _parser = SilentParser(start, end)
    return _parser


def render(text: str, context: typing.Any = None) -> str:
    """Parse and render shortcodes."""
    parser = _get_parser()

    try:
        return parser.parse(text, context)
    except shortcodes.ShortcodeError as e:
        log.warning('Error rendering tag: %s', e)
        return text
