import time
from io import StringIO
from typing import Optional

import meilisearch
from django.conf import settings
from django.core.management import call_command
from django.test.testcases import TestCase

from common.tests.factories.blog import RevisionFactory
from common.tests.factories.films import FilmFactory, AssetFactory
from common.tests.factories.training import TrainingFactory, SectionFactory
from training.models import TrainingStatus


class BaseSearchTestCase(TestCase):
    TEST_INDEX_UID = 'test-studio'
    index: Optional[meilisearch.index.Index]

    @classmethod
    def setUpClass(cls) -> None:
        client: meilisearch.client.Client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
        cls.index = client.get_or_create_index(cls.TEST_INDEX_UID, {'primaryKey': 'search_id'})
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.index.delete()
        super().tearDownClass()

    def meilisearch_available(self):
        try:
            self.index.info()
        except meilisearch.errors.MeiliSearchCommunicationError:
            return False
        return True

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
        # The signals for these factories are muted. Create 15 object to be indexed:
        film = FilmFactory()
        AssetFactory.create_batch(2, film=film)
        training_1, *_ = TrainingFactory.create_batch(3, status=TrainingStatus.published.name)
        SectionFactory.create_batch(4, chapter__training=training_1)
        RevisionFactory.create_batch(5, post__film=film)

        # Create some additional objects which do not qualify for indexing:
        unpublished_film = FilmFactory(is_published=False)
        AssetFactory(film=unpublished_film)
        AssetFactory(is_published=False, film=film)
        unpublished_training = TrainingFactory(status=TrainingStatus.unpublished.name)
        SectionFactory(chapter__training=unpublished_training)
        RevisionFactory(post__is_published=False, post__film=film)
        RevisionFactory(is_published=False, post__film=film)

    def test_index_documents_command(self):
        if not self.meilisearch_available():
            self.skipTest('MeiliSearch server does not seem to be running')
        initial_docs_count = self.index.get_stats()['numberOfDocuments']
        out = StringIO()
        update_id = call_command('index_documents', index=self.TEST_INDEX_UID, stdout=out)

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
    def setUpClass(cls) -> None:
        pass
