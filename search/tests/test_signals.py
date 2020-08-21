from unittest.mock import patch

from django.db.models.signals import post_save, pre_delete
from django.test.testcases import TestCase

from blog.models import Revision, Post
from common.tests.factories.blog import PostFactory
from common.tests.factories.films import FilmFactory
from common.tests.factories.helpers import generate_file_path, catch_signal
from common.tests.factories.static_assets import StorageLocationFactory
from common.tests.factories.users import UserFactory
from films.models import Film, FilmStatus


class TestBlogPostIndexing(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.storage = StorageLocationFactory()
        cls.published_post = PostFactory(film=None)
        cls.unpublished_post = PostFactory(is_published=False, film=None)
        cls.revision_data = {
            'editor': cls.user,
            'title': 'Strawberry Fields Forever',
            'topic': 'Announcement',
            'content': '# Hot news',
            'storage_location': cls.storage,
            'picture_16_9': generate_file_path(),
        }

    def test_blog_post_without_revision_does_not_trigger_post_save_signal(self):
        with catch_signal(post_save, sender=Revision) as handler:
            post = Post.objects.create(author=self.user, slug='empty-post')
            handler.assert_not_called()

            post.is_published = True
            post.save()
            handler.assert_not_called()

    @patch('search.signals.MainPostSaveSearchIndexer._add_documents_to_index')
    def test_unpublished_revisions_are_not_indexed(self, add_documents_mock):
        Revision.objects.create(
            **self.revision_data, post=self.published_post, is_published=False,
        )
        add_documents_mock.assert_not_called()

        Revision.objects.create(
            **self.revision_data, post=self.unpublished_post, is_published=True,
        )
        add_documents_mock.assert_not_called()

    @patch('search.signals.MainPostSaveSearchIndexer._add_documents_to_index')
    def test_new_published_revision_triggers_signal(self, add_documents_mock):
        revision = Revision.objects.create(
            **self.revision_data, post=self.published_post, is_published=True,
        )
        add_documents_mock.assert_called_once()

    @patch('search.signals.MainPostSaveSearchIndexer._add_documents_to_index')
    def test_new_published_revision_overwrites_previous_revision(self, add_documents_mock):
        """A document is updated in the index if it has the same search_id."""
        revision = Revision.objects.create(
            **self.revision_data, post=self.published_post, is_published=True,
        )

        add_documents_mock.assert_called_once()

        search_id_1 = add_documents_mock.call_args_list[0].args[0][0]['search_id']
        mock_arg_name = add_documents_mock.call_args_list[0].args[0][0]['name']
        initial_title = self.revision_data['title']

        self.assertEqual(mock_arg_name, initial_title)

        new_title = 'I am the Walrus'
        new_revision_data = {**self.revision_data, 'title': new_title}
        new_revision = Revision.objects.create(
            **new_revision_data, post=self.published_post, is_published=True,
        )

        self.assertEqual(add_documents_mock.call_count, 2)

        search_id_2 = add_documents_mock.call_args_list[1].args[0][0]['search_id']
        mock_arg_name = add_documents_mock.call_args_list[1].args[0][0]['name']

        self.assertEqual(mock_arg_name, new_title)
        self.assertEqual(search_id_1, search_id_2)


class TestPostDeleteSignal(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.storage = StorageLocationFactory()
        cls.film_data = {
            'storage_location': cls.storage,
            'title': 'Strawberry Fields Forever',
            'slug': 'strawberry-fields-forever',
            'description': 'Living is easy with eyes closed',
            'summary': 'Misunderstanding all you see',
            'status': FilmStatus.released.value,
            'is_published': True,
            'logo': generate_file_path(),
            'poster': generate_file_path(),
            'picture_header': generate_file_path(),
        }

    def setUp(self) -> None:
        self.film_not_indexed = FilmFactory()

    def test_deleting_not_indexed_film_triggers_signal(self):
        with catch_signal(pre_delete, sender=Film) as handler:
            self.film_not_indexed.delete()
            handler.assert_called()

    def test_deleting_indexed_film(self):
        film = Film.objects.create(**self.film_data)

        with catch_signal(pre_delete, sender=Film) as handler:
            film.delete()
            handler.assert_called()
