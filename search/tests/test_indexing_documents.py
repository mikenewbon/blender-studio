import time
from io import StringIO
from typing import Optional
from unittest.case import skipIf
from unittest.mock import patch

import meilisearch
from django.conf import settings
from django.core.management import call_command
from django.db.models.signals import post_save
from django.test.testcases import TestCase

from blog.models import Post, Revision
from common.tests.factories.blog import RevisionFactory, PostFactory
from common.tests.factories.films import FilmFactory, AssetFactory
from common.tests.factories.helpers import catch_signal, generate_file_path
from common.tests.factories.static_assets import StorageLocationFactory
from common.tests.factories.training import TrainingFactory, SectionFactory
from common.tests.factories.users import UserFactory
from training.models import TrainingStatus

TEST_INDEX_UID = 'test-studio'


def meilisearch_available():
    client: meilisearch.client.Client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
    try:
        client.health()
    except meilisearch.errors.MeiliSearchCommunicationError:
        return False
    return True


@skipIf(not meilisearch_available(), 'MeiliSearch server does not seem to be running')
class BaseSearchTestCase(TestCase):
    TEST_INDEX_UID = 'test-studio'
    index: Optional[meilisearch.index.Index]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        client: meilisearch.client.Client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
        cls.index = client.get_or_create_index(TEST_INDEX_UID, {'primaryKey': 'search_id'})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.index.delete()
        super().tearDownClass()

    def wait_for_update_execution(self, update_id: int) -> str:
        """If the update is enqueued, wait for its status to change.

        On index update, the update is enqueued, but not always processed quickly enough.
        This method fails the test after a timeout of ca. 5 seconds.
        """
        timeout_in_seconds = 5
        update_data = self.index.get_update_status(update_id)
        while update_data['status'] == 'enqueued':
            time.sleep(0.5)
            timeout_in_seconds -= 0.5
            if timeout_in_seconds <= 0:
                self.fail(
                    f'Timeout: update id={update_id} enqueued, but not processed. '
                    f'Update status: \'{update_data["status"]}\''
                )
            update_data = self.index.get_update_status(update_id)

        return update_data["status"]


class TestIndexDocumentsCommand(BaseSearchTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # The signals for these factories are muted. Create 15 objects to be indexed:
        film = FilmFactory()
        AssetFactory.create_batch(2, film=film)
        training_1, *_ = TrainingFactory.create_batch(3, status=TrainingStatus.published.name)
        SectionFactory.create_batch(4, chapter__training=training_1)
        _post = PostFactory(film=film)
        RevisionFactory.create_batch(2, post=_post)  # only the latest revision gets indexed
        RevisionFactory.create_batch(4, post__film=film)

        # Create some additional objects which do not qualify for indexing:
        unpublished_film = FilmFactory(is_published=False)
        AssetFactory(film=unpublished_film)
        AssetFactory(is_published=False, film=film)
        unpublished_training = TrainingFactory(status=TrainingStatus.unpublished.name)
        SectionFactory(chapter__training=unpublished_training)
        RevisionFactory(post__is_published=False, post__film=film)
        RevisionFactory(is_published=False, post__film=film)

    def test_index_documents_command(self):
        initial_docs_count = self.index.get_stats()['numberOfDocuments']
        out = StringIO()
        update_id = call_command('index_documents', index=TEST_INDEX_UID, stdout=out)

        self.assertIn('Successfully', out.getvalue())
        self.assertIn('15 objects to load', out.getvalue())
        update_data = self.index.get_update_status(update_id)
        self.assertEqual(update_data['type']['number'], 15)
        if update_data['status'] == 'enqueued':
            update_status = self.wait_for_update_execution(update_id)

        self.assertEqual(update_status, 'processed')
        self.assertEqual(self.index.get_stats()['numberOfDocuments'], initial_docs_count + 15)


class TestBlogPostIndexing(BaseSearchTestCase):
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

    @patch('search.signals.add_documents')
    def test_unpublished_revisions_are_not_indexed(self, add_documents_mock):
        Revision.objects.create(
            **self.revision_data, post=self.published_post, is_published=False,
        )
        add_documents_mock.assert_not_called()

        Revision.objects.create(
            **self.revision_data, post=self.unpublished_post, is_published=True,
        )
        add_documents_mock.assert_not_called()

    @patch('search.signals.add_documents')
    def test_new_published_revision_triggers_signal(self, add_documents_mock):
        revision = Revision.objects.create(
            **self.revision_data, post=self.published_post, is_published=True,
        )
        add_documents_mock.assert_called_once()

    def test_new_published_revision_overwrites_previous_revision(self):
        revision = Revision.objects.create(
            **self.revision_data, post=self.published_post, is_published=True,
        )
        time.sleep(0.5)
        search_id = f'post_{revision.post.id}'
        response = self.index.get_document(search_id)
        self.assertEqual(response['title'], 'Strawberry Fields Forever')

        new_revision_data = {
            **self.revision_data,
            'title': 'I am the Walrus',
        }

        new_revision = Revision.objects.create(
            **new_revision_data, post=self.published_post, is_published=True,
        )
        time.sleep(0.5)
        response = self.index.get_document(search_id)
        self.assertEqual(response['title'], 'I am the Walrus')
