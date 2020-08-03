from django.test.testcases import TestCase
from django.urls import reverse

from common.queries import DEFAULT_FEED_PAGE_SIZE
from common.tests.factories.blog import RevisionFactory, PostFactory
from common.tests.factories.films import ProductionLogFactory
from common.tests.factories.training import TrainingFactory


class TestActivityFeedEndpoint(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        ProductionLogFactory.create_batch(5)
        TrainingFactory.create_batch(5)
        RevisionFactory.create_batch(5)
        ProductionLogFactory.create_batch(4)
        TrainingFactory.create_batch(4)
        post = PostFactory()
        RevisionFactory.create_batch(4, post=post)  # only one (the latest) revision counts

        cls.home_url = reverse('home')

    def test_homepage_gets_latest_records(self):
        response = self.client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('records', response.context)
        records = response.context['records']
        self.assertEqual(len(records), DEFAULT_FEED_PAGE_SIZE)
        types = [r['obj_type'] for r in records]
        self.assertEqual(types.count('training'), 4)
        self.assertEqual(types.count('production log'), 4)
        self.assertEqual(types.count('post'), 2)
