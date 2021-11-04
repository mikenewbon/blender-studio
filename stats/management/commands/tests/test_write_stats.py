from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from common.tests.factories.blog import PostFactory
from common.tests.factories.comments import CommentFactory
from common.tests.factories.films import AssetFactory
from common.tests.factories.static_assets import StaticAssetFactory
from common.tests.factories.users import UserFactory
from stats.models import Sample, StaticAssetView, StaticAssetDownload, StaticAssetCountedVisit


class WriteStatsCommandTest(TestCase):
    def test_command_all_zero(self):
        out = StringIO()

        call_command('write_stats', stdout=out)

        self.assertEqual(Sample.objects.count(), 6)
        sample = Sample.objects.first()
        self.assertEqual(sample.value, 0)

    def test_command(self):
        # some comments
        for _ in range(2):
            CommentFactory()
        # some deleted comments
        for _ in range(1):
            CommentFactory(date_deleted='2021-08-01 10:10:10')
        # some subscribers
        for _ in range(5):
            user = UserFactory()
            user.groups.add(Group.objects.get_or_create(name='subscriber')[0])
        # some demo users
        for _ in range(3):
            user = UserFactory()
            user.groups.add(Group.objects.get_or_create(name='demo')[0])
        # some inactive demo users, shouldn't be counted
        for _ in range(2):
            user = UserFactory(is_active=False)
            user.groups.add(Group.objects.get_or_create(name='demo')[0])
        # some blog posts
        for _ in range(3):
            PostFactory(is_published=True)
        # some unpusblished blog posts, shouldn't be counted
        for _ in range(1):
            PostFactory(is_published=False)
        # some film assets
        for _ in range(2):
            AssetFactory(is_published=True)
        # some unpublished film assets, shouldn't be counted
        for _ in range(1):
            AssetFactory(is_published=False)

        out = StringIO()
        call_command('write_stats', stdout=out)

        self.assertEqual(Sample.objects.count(), 6)
        blog_posts_count_sample = Sample.objects.get(slug='blog_posts_count')
        comments_count_sample = Sample.objects.get(slug='comments_count')
        film_assets_count_sample = Sample.objects.get(slug='film_assets_count')
        users_demo_count_sample = Sample.objects.get(slug='users_demo_count')
        users_subscribers_count_sample = Sample.objects.get(slug='users_subscribers_count')
        users_total_count_sample = Sample.objects.get(slug='users_total_count')

        self.assertEqual(blog_posts_count_sample.value, 3)
        self.assertEqual(comments_count_sample.value, 2)
        self.assertEqual(film_assets_count_sample.value, 2)
        self.assertEqual(users_demo_count_sample.value, 3)
        self.assertEqual(users_subscribers_count_sample.value, 5)
        # includes users created along with the comments and blog posts
        self.assertEqual(users_total_count_sample.value, 18)

    def test_command_updates_static_assets_view_counters(self):
        out = StringIO()
        static_asset = StaticAssetFactory()
        StaticAssetView.objects.bulk_create(
            [
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.11'),
            ]
        )
        old_date_updated = static_asset.date_updated

        call_command('write_stats', stdout=out)

        static_asset.refresh_from_db()
        self.assertEqual(static_asset.view_count, 2)
        self.assertEqual(static_asset.download_count, 0)
        # auto-update field should not have changed on recount
        self.assertEqual(old_date_updated, static_asset.date_updated)
        # tables storing individual views still have them
        self.assertEqual(StaticAssetView.objects.count(), 2)
        self.assertEqual(StaticAssetDownload.objects.count(), 0)
        # last seen ID for this counter should have been stored
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='view_count').last_seen_id,
            StaticAssetView.objects.order_by('-id').first().pk,
        )
        self.assertEqual(StaticAssetCountedVisit.objects.filter(field='download_count').count(), 0)

    def test_command_updates_static_assets_download_counters(self):
        out = StringIO()
        static_asset = StaticAssetFactory()
        StaticAssetDownload.objects.bulk_create(
            [
                StaticAssetDownload(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetDownload(static_asset_id=static_asset.pk, ip_address='192.19.10.11'),
            ]
        )
        old_date_updated = static_asset.date_updated

        call_command('write_stats', stdout=out)

        static_asset.refresh_from_db()
        self.assertEqual(static_asset.view_count, 0)
        self.assertEqual(static_asset.download_count, 2)
        # auto-update field should not have changed on recount
        self.assertEqual(old_date_updated, static_asset.date_updated)
        # tables storing individual views still have them
        self.assertEqual(StaticAssetView.objects.count(), 0)
        self.assertEqual(StaticAssetDownload.objects.count(), 2)
        # last seen ID for this counter should have been stored
        self.assertEqual(StaticAssetCountedVisit.objects.filter(field='view_count').count(), 0)
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='download_count').last_seen_id,
            StaticAssetDownload.objects.order_by('-id').first().pk,
        )

    def test_command_adds_static_assets_view_counters(self):
        out = StringIO()
        static_asset = StaticAssetFactory(view_count=10)
        StaticAssetView.objects.bulk_create(
            [
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.11'),
            ]
        )
        old_date_updated = static_asset.date_updated

        call_command('write_stats', stdout=out)

        static_asset.refresh_from_db()
        self.assertEqual(static_asset.view_count, 12)
        self.assertEqual(static_asset.download_count, 0)
        # auto-update field should not have changed on recount
        self.assertEqual(old_date_updated, static_asset.date_updated)
        # tables storing individual views still have them
        self.assertEqual(StaticAssetView.objects.count(), 2)
        self.assertEqual(StaticAssetDownload.objects.count(), 0)
        # last seen ID for this counter should have been stored
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='view_count').last_seen_id,
            StaticAssetView.objects.order_by('-id').first().pk,
        )
        self.assertEqual(StaticAssetCountedVisit.objects.filter(field='download_count').count(), 0)

    def test_command_adds_static_assets_download_counters(self):
        out = StringIO()
        static_asset = StaticAssetFactory(download_count=10)
        StaticAssetDownload.objects.bulk_create(
            [
                StaticAssetDownload(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetDownload(static_asset_id=static_asset.pk, ip_address='192.19.10.11'),
            ]
        )
        old_date_updated = static_asset.date_updated

        call_command('write_stats', stdout=out)

        static_asset.refresh_from_db()
        self.assertEqual(static_asset.view_count, 0)
        self.assertEqual(static_asset.download_count, 12)
        # auto-update field should not have changed on recount
        self.assertEqual(old_date_updated, static_asset.date_updated)
        # tables storing individual views still have them
        self.assertEqual(StaticAssetView.objects.count(), 0)
        self.assertEqual(StaticAssetDownload.objects.count(), 2)
        # last seen ID for this counter should have been stored
        self.assertEqual(StaticAssetCountedVisit.objects.filter(field='view_count').count(), 0)
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='download_count').last_seen_id,
            StaticAssetDownload.objects.order_by('-id').first().pk,
        )

    def test_command_updates_static_assets_both_download_and_view_counters(self):
        out = StringIO()
        static_asset = StaticAssetFactory(download_count=5, view_count=4)
        StaticAssetView.objects.bulk_create(
            [
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.11'),
            ]
        )
        StaticAssetDownload.objects.bulk_create(
            [
                StaticAssetDownload(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetDownload(static_asset_id=static_asset.pk, ip_address='192.19.10.11'),
            ]
        )
        old_date_updated = static_asset.date_updated

        call_command('write_stats', stdout=out)

        static_asset.refresh_from_db()
        self.assertEqual(static_asset.view_count, 6)
        self.assertEqual(static_asset.download_count, 7)
        # auto-update field should not have changed on recount
        self.assertEqual(old_date_updated, static_asset.date_updated)
        # tables storing individual views still have them
        self.assertEqual(StaticAssetView.objects.count(), 2)
        self.assertEqual(StaticAssetDownload.objects.count(), 2)
        # last seen ID for both counters should have been stored
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='view_count').last_seen_id,
            StaticAssetView.objects.order_by('-id').first().pk,
        )
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='download_count').last_seen_id,
            StaticAssetDownload.objects.order_by('-id').first().pk,
        )

    def test_command_updates_static_assets_both_download_and_view_counters_uses_last_seen_id(self):
        out = StringIO()
        initial_view_count, initial_download_count = 4, 5
        static_asset = StaticAssetFactory(
            download_count=initial_download_count, view_count=initial_view_count
        )
        download_count_starts_here = StaticAssetDownload(
            static_asset_id=static_asset.pk, ip_address='192.19.10.15'
        )
        view_count_starts_here = StaticAssetView(
            static_asset_id=static_asset.pk, ip_address='192.19.10.13'
        )
        view_next = StaticAssetView(static_asset_id=static_asset.pk, ip_address='127.0.0.1')
        download_next = StaticAssetDownload(
            static_asset_id=static_asset.pk, ip_address='192.19.10.11'
        )
        StaticAssetView.objects.bulk_create(
            [
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetView(static_asset_id=static_asset.pk, ip_address='192.19.10.11'),
                view_count_starts_here,
                StaticAssetView(static_asset_id=static_asset.pk, user_id=15),
                StaticAssetView(static_asset_id=static_asset.pk, user_id=16),
                view_next,
            ]
        )
        StaticAssetDownload.objects.bulk_create(
            [
                StaticAssetDownload(static_asset_id=static_asset.pk, ip_address='192.19.10.10'),
                StaticAssetDownload(static_asset_id=static_asset.pk, user_id=66),
                download_count_starts_here,
                StaticAssetDownload(static_asset_id=static_asset.pk, user_id=1324),
                download_next,
            ]
        )
        StaticAssetCountedVisit.objects.bulk_create(
            [
                StaticAssetCountedVisit(field='view_count', last_seen_id=view_count_starts_here.pk),
                StaticAssetCountedVisit(
                    field='download_count', last_seen_id=download_count_starts_here.pk
                ),
            ]
        )
        old_date_updated = static_asset.date_updated

        call_command('write_stats', stdout=out)

        static_asset.refresh_from_db()
        self.assertEqual(static_asset.view_count, initial_view_count + 3)
        self.assertEqual(static_asset.download_count, initial_download_count + 2)
        # auto-update field should not have changed on recount
        self.assertEqual(old_date_updated, static_asset.date_updated)
        # tables storing individual views still have them
        self.assertEqual(StaticAssetView.objects.count(), 6)
        self.assertEqual(StaticAssetDownload.objects.count(), 5)
        # last seen ID for both counters should have been stored
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='view_count').last_seen_id,
            view_next.pk,
        )
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='download_count').last_seen_id,
            download_next.pk,
        )

        # do another count
        call_command('write_stats', stdout=out)

        # no changes, because no new visits recorded
        static_asset.refresh_from_db()
        self.assertEqual(static_asset.view_count, initial_view_count + 3)
        self.assertEqual(static_asset.download_count, initial_download_count + 2)
        self.assertEqual(StaticAssetView.objects.count(), 6)
        self.assertEqual(StaticAssetDownload.objects.count(), 5)
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='view_count').last_seen_id,
            view_next.pk,
        )
        self.assertEqual(
            StaticAssetCountedVisit.objects.get(field='download_count').last_seen_id,
            download_next.pk,
        )
