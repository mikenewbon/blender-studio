from unittest.mock import patch

from django.db.models.signals import post_save, pre_delete
from django.test.testcases import TestCase

from blog.models import Post
from common.tests.factories.films import FilmFactory
from common.tests.factories.helpers import generate_file_path, catch_signal
from common.tests.factories.users import UserFactory
from films.models import Film, FilmStatus


class TestBlogPostIndexing(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.post_data = {
            'author': cls.user,
            'title': 'Strawberry Fields Forever',
            'category': 'Announcement',
            'content': '# Hot news',
            'thumbnail': generate_file_path(),
        }

    @patch('search.signals.check_meilisearch')
    @patch('django.conf.settings.SEARCH_CLIENT')
    def test_unpublished_posts_trigger_signal_but_are_not_indexed(
        self, search_client_mock, check_meilisearch_mock
    ):
        with catch_signal(post_save, sender=Post) as handler:
            Post.objects.create(**self.post_data, is_published=False)
            handler.assert_called()
            check_meilisearch_mock.assert_called_once()
            search_client_mock.assert_not_called()

    @patch('search.signals.check_meilisearch')
    @patch('django.conf.settings.SEARCH_CLIENT')
    def test_new_published_posts_are_indexed(self, search_client_mock, check_meilisearch_mock):
        Post.objects.create(**self.post_data, is_published=True)
        check_meilisearch_mock.assert_called_once()
        search_client_mock.get_index.return_value.add_documents.assert_called()


class TestPostDeleteSignal(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.film_data = {
            'title': 'Strawberry Fields Forever',
            'slug': 'strawberry-fields-forever',
            'description': 'Living is easy with eyes closed',
            'summary': 'Misunderstanding all you see',
            'status': FilmStatus.released.value,
            'is_published': True,
            'logo': generate_file_path(),
            'poster': generate_file_path(),
            'picture_header': generate_file_path(),
            'thumbnail': generate_file_path(),
        }

    def setUp(self) -> None:
        self.film_not_indexed = FilmFactory()

    def test_deleting_not_indexed_film_triggers_signal(self):
        with catch_signal(pre_delete, sender=Film) as handler:
            self.film_not_indexed.delete()
            handler.assert_called()

    def test_deleting_indexed_film_triggers_signal(self):
        film = Film.objects.create(**self.film_data)

        with catch_signal(pre_delete, sender=Film) as handler:
            film.delete()
            handler.assert_called()
