from io import StringIO
from typing import Optional
from unittest.case import skipIf

import meilisearch
from django.conf import settings
from django.core.management import call_command
from django.test.testcases import TestCase

from common.tests.factories.blog import RevisionFactory, PostFactory
from common.tests.factories.films import FilmFactory, AssetFactory
from common.tests.factories.training import TrainingFactory, SectionFactory
from training.models import TrainingStatus

TEST_INDEX_UID = 'test_studio'


def meilisearch_available():
    try:
        settings.SEARCH_CLIENT.health()
    except meilisearch.errors.MeiliSearchCommunicationError:
        return False
    return True


@skipIf(not meilisearch_available(), 'MeiliSearch server does not seem to be running')
class BaseSearchTestCase(TestCase):
    index: Optional[meilisearch.index.Index]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        for index_uid in [*settings.INDEXES_FOR_SORTING.keys(), settings.TRAINING_INDEX_UID]:
            settings.SEARCH_CLIENT.get_or_create_index(index_uid, {'primaryKey': 'search_id'})
        cls.index = settings.MAIN_SEARCH_INDEX
        assert cls.index.uid == TEST_INDEX_UID

    @classmethod
    def tearDownClass(cls) -> None:
        for index_uid in settings.INDEXES_FOR_SORTING.keys():
            settings.SEARCH_CLIENT.get_index(index_uid).delete()
        super().tearDownClass()


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
        update_id = call_command('index_documents', stdout=out)

        self.assertIn('Successfully', out.getvalue())
        self.assertIn('15 objects to load', out.getvalue())
        update_data = self.index.wait_for_pending_update(update_id)
        self.assertEqual(update_data['status'], 'processed')
        self.assertEqual(update_data['type']['number'], 15)
        self.assertEqual(self.index.get_stats()['numberOfDocuments'], initial_docs_count + 15)
