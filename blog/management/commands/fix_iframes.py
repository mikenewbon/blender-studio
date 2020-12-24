"""Find all podcast posts and change update their broken SoundCloud embeds."""
import logging
import re
import xml.etree.ElementTree as ET

from django.contrib.sites.shortcuts import get_current_site
from django.core.management.base import BaseCommand
from django.db.models import Q

from blog.models import Post

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

audio_tmpl = '''
<p class="audio-container">
  <audio controls>
    <source src="{url}" type="audio/mp4">
  </audio>
  <a href="{url}" download class="btn btn-sm btn-dark">Download</a>
</p>
'''


def _url(path):
    request = None
    return ''.join(['http://', get_current_site(request).domain, path])


class Command(BaseCommand):
    """Create Mailgun unsubscribes for users who have is_subscribed_to_newsletter==False."""

    def handle(self, *args, **options):  # noqa: D102
        # http://podcast.blender.institute/feed.xml
        root = ET.parse('feed.xml').getroot()
        items = [item for item in root.getchildren()[0].getchildren() if item.tag == 'item']
        audio_url = {
            re.search(r'#\d+', item.getchildren()[0].text)
            .group(): next(c for c in item.getchildren() if c.tag == 'enclosure')
            .attrib['url']
            for item in items
        }
        podcasts = Post.objects.filter(content__icontains='<iframe').filter(
            Q(title__icontains='podcast')
        )
        assert len(audio_url) >= podcasts.count(), f'{len(audio_url)} !>= {podcasts.count()}'
        for post in podcasts:
            num = re.search(r'#\d+', post.title).group()
            url = audio_url.pop(num, None)
            if not url:
                logger.warning('Unable to find %s in the feed', post.title)
                continue
            post.content = re.sub(r'<iframe.*iframe\s*>', audio_tmpl.format(url=url), post.content)
            post.save(update_fields=['content_html', 'content'])
            logger.info('Updated %s', _url(post.url))
        # if audio_url:
        #    logger.warning('Leftover audio %s', audio_url)
        other_iframes = Post.objects.filter(content__icontains='<iframe').exclude(
            Q(title__icontains='podcast')
        )
        for post in other_iframes:
            youtube_iframe = re.findall(r'.iframe..*..iframe.', post.content)
            youtube_iframe = youtube_iframe[0] if youtube_iframe else None
            if youtube_iframe:
                youtube_id = None
                youtube_link = re.findall(r'src=.([^"\']+)', youtube_iframe)
                youtube_link = youtube_link[0] if youtube_link else None
                if 'embed/' in youtube_link:
                    youtube_id = youtube_link.split('embed/')[-1]
                else:
                    youtube_id = youtube_link.split('v=')[-1]
                if youtube_id:
                    youtube_id = re.search(r'[^%\?=]+', youtube_id).group()
                    post.content = post.content.replace(
                        youtube_iframe, '{youtube ' + youtube_id + '}'
                    )
                    post.save(update_fields=['content_html', 'content'])
                    logger.info('Updated %s', _url(post.url))
