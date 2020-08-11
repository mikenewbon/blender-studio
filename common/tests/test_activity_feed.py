from django.test.testcases import TestCase

from blog.models import Revision
from common.queries import DEFAULT_FEED_PAGE_SIZE, get_activity_feed_page
from common.tests.factories.blog import RevisionFactory, PostFactory
from common.tests.factories.films import ProductionLogFactory
from common.tests.factories.training import TrainingFactory
from search import signals as search_signals
from search.signals import update_search_index
from training.models import Training


class TestActivityFeedEndpoint(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        search_signals.post_save.disconnect(update_search_index, Revision)
        search_signals.post_save.disconnect(update_search_index, Training)

        ProductionLogFactory.create_batch(5)
        TrainingFactory.create_batch(5)
        RevisionFactory.create_batch(5)
        ProductionLogFactory.create_batch(4)
        TrainingFactory.create_batch(4)
        post = PostFactory()
        RevisionFactory.create_batch(4, post=post)  # only one (the latest) revision counts

    def test_homepage_gets_latest_records(self):
        records = get_activity_feed_page()

        self.assertEqual(len(records), DEFAULT_FEED_PAGE_SIZE)
        types = [r['obj_type'] for r in records]
        self.assertEqual(types.count('training'), 4)
        self.assertEqual(types.count('production log'), 4)
        self.assertEqual(types.count('post'), 2)
