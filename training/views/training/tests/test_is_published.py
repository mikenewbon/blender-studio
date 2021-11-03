from unittest.mock import patch, Mock

from django.test.testcases import TestCase
import responses

from common.tests.factories.training import SectionFactory, ChapterFactory, TrainingFactory
from common.tests.factories.users import UserFactory


class _BaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.staff_user = UserFactory(is_staff=True, is_superuser=False)
        self.superuser = UserFactory(is_staff=False, is_superuser=True)
        self.user = UserFactory(is_staff=False, is_superuser=False)

        # Patch away everything that has to do with storage and thumbnails
        for _patch in (
            patch('sorl.thumbnail.shortcuts.get_thumbnail', Mock(return_value='')),
            patch('sorl.thumbnail.templatetags.thumbnail.get_thumbnail', Mock(return_value='')),
            patch('storages.backends.s3boto3.S3Boto3Storage.url', Mock(return_value='s3://file')),
            patch('storages.backends.s3boto3.S3Boto3Storage.exists', Mock(return_value=True)),
        ):
            _patch.start()
            self.addCleanup(_patch.stop)

        # and anything requests-related
        self.responses = responses.RequestsMock()
        self.responses.start()
        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)


class _AlwaysAvailableToStaffMixin:
    def test_staff_200(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 200)

    def test_superuser_200(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 200)


class TestChapterAlwaysAvailableToStaffMixin:
    def test_staff_200(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 200)

    def test_superuser_200(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 200)


class TestTrainingAlwaysAvailableToStaffMixin:
    def test_staff_200(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(self.training.url)

        self.assertEqual(response.status_code, 200)

    def test_superuser_200(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.training.url)

        self.assertEqual(response.status_code, 200)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestSectionIsPublishedYes(_AlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.section = SectionFactory(
            is_published=True,
            chapter__is_published=True,
            chapter__training__is_published=True,
            static_asset=None,
        )

    def test_anon_200(self):
        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 200)

    def test_user_200(self):
        self.client.force_login(self.user)

        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 200)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestSectionIsPublishedNo(_AlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.section = SectionFactory(
            is_published=False, chapter__is_published=True, chapter__training__is_published=True
        )

    def test_anon_302(self):
        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 302)

    def test_user_302(self):
        self.client.force_login(self.user)

        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 302)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestSectionIsPublishedYesChapterNo(_AlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.section = SectionFactory(
            is_published=True, chapter__is_published=False, chapter__training__is_published=True
        )

    def test_anon_302(self):
        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 302)

    def test_user_302(self):
        self.client.force_login(self.user)

        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 302)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestSectionIsPublishedYesTrainingNo(_AlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.section = SectionFactory(
            is_published=True, chapter__is_published=True, chapter__training__is_published=False
        )

    def test_anon_302(self):
        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 302)

    def test_user_302(self):
        self.client.force_login(self.user)

        response = self.client.get(self.section.url)

        self.assertEqual(response.status_code, 302)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestChapterIsPublishedYes(TestChapterAlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.chapter = ChapterFactory(is_published=True, training__is_published=True)

    def test_anon_200(self):
        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 200)

    def test_user_200(self):
        self.client.force_login(self.user)

        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 200)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestChapterIsPublishedNo(TestChapterAlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.chapter = ChapterFactory(is_published=False, training__is_published=True)

    def test_anon_302(self):
        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 302)

    def test_user_302(self):
        self.client.force_login(self.user)

        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 302)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestChapterIsPublishedYesTrainingNo(TestChapterAlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.chapter = ChapterFactory(is_published=True, training__is_published=False)

    def test_anon_302(self):
        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 302)

    def test_user_302(self):
        self.client.force_login(self.user)

        response = self.client.get(self.chapter.url)

        self.assertEqual(response.status_code, 302)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestTrainingIsPublishedYes(TestTrainingAlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.training = TrainingFactory(is_published=True)

    def test_anon_200(self):
        response = self.client.get(self.training.url)

        self.assertEqual(response.status_code, 200)

    def test_user_200(self):
        self.client.force_login(self.user)

        response = self.client.get(self.training.url)

        self.assertEqual(response.status_code, 200)


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestTrainingIsPublishedNo(TestTrainingAlwaysAvailableToStaffMixin, _BaseTestCase):
    def setUp(self):
        super().setUp()
        self.training = TrainingFactory(is_published=False)

    def test_anon_404(self):
        response = self.client.get(self.training.url)

        self.assertEqual(response.status_code, 404)

    def test_user_404(self):
        self.client.force_login(self.user)

        response = self.client.get(self.training.url)

        self.assertEqual(response.status_code, 404)
