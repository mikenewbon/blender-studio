"""Write stats data."""
import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from comments.models import Comment
from films.models import Asset
from stats.models import Sample, StaticAssetView, StaticAssetDownload
from blog.models import Post

logger = logging.getLogger('write_stats')
logger.setLevel(logging.DEBUG)
User = get_user_model()


class Command(BaseCommand):
    """Write stats data."""

    def _get_comments_count(self):
        return Comment.objects.filter(date_deleted__isnull=True).count()

    def _get_film_assets_count(self):
        return Asset.objects.filter(is_published=True).count()

    def _get_blog_posts_count(self):
        return Post.objects.filter(is_published=True).count()

    def _get_users_total_count(self):
        return User.objects.filter(is_active=True).count()

    def _get_users_subscribers_count(self):
        return User.objects.filter(is_active=True, groups__name='subscriber').distinct().count()

    def _get_users_demo_count(self):
        return User.objects.filter(is_active=True, groups__name='demo').distinct().count()

    def write_samples(self):
        """Run some counting queries and write their results into Sample table."""
        timestamp = timezone.now()
        Sample.objects.bulk_create(
            [
                Sample(
                    timestamp=timestamp,
                    slug='comments_count',
                    value=self._get_comments_count(),
                ),
                Sample(
                    timestamp=timestamp,
                    value=self._get_film_assets_count(),
                    slug='film_assets_count',
                ),
                Sample(
                    timestamp=timestamp,
                    slug='blog_posts_count',
                    value=self._get_blog_posts_count(),
                ),
                Sample(
                    timestamp=timestamp,
                    slug='users_total_count',
                    value=self._get_users_total_count(),
                ),
                Sample(
                    timestamp=timestamp,
                    slug='users_subscribers_count',
                    value=self._get_users_subscribers_count(),
                ),
                Sample(
                    timestamp=timestamp,
                    slug='users_demo_count',
                    value=self._get_users_demo_count(),
                ),
            ]
        )

    def write_static_asset_counts(self):
        """Calculate view and download counts for StaticAssets."""
        StaticAssetView.update_counters(to_field='view_count')
        StaticAssetDownload.update_counters(to_field='download_count')

    def handle(self, *args, **options):
        """Write various stats."""
        self.write_samples()
        self.write_static_asset_counts()
