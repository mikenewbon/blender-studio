from unittest.mock import patch, Mock

from django.db.utils import IntegrityError
from django.test.testcases import TestCase
from django.urls import reverse

from common.tests.factories.training import TrainingFactory, TrainingFlatPageFactory
from training.models import TrainingFlatPage


class TestTrainingFlatPageModel(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.training_1 = TrainingFactory()
        cls.training_2 = TrainingFactory()
        cls.flatpage_data = {
            'training': cls.training_1,
            'title': 'About',
            'content': '# hello world',
        }

    def test_slug_and_content_html_created_on_save(self):
        flatpage = TrainingFlatPage.objects.create(
            training=self.training_1, title='New Page', content='# hello world'
        )
        self.assertEqual(flatpage.slug, 'new-page')
        self.assertHTMLEqual(flatpage.content_html, '<h1>hello world</h1>')

    def test_slug_created_only_if_not_provided(self):
        custom_slug = 'custom'
        flatpage = TrainingFlatPage.objects.create(
            training=self.training_1, title='New Page', slug=custom_slug, content='# hello world'
        )
        self.assertEqual(flatpage.slug, custom_slug)

    def test_create_pages_with_same_slugs_for_different_trainings(self):
        assert self.training_1.slug != self.training_2.slug
        try:
            page_1 = TrainingFlatPage.objects.create(
                training=self.training_1, title='New Page', content='# hello world'
            )
            page_2 = TrainingFlatPage.objects.create(
                training=self.training_2, title='New Page', content='# hello world'
            )
        except IntegrityError as err:
            self.fail(
                f'It should be possible to create flat pages with the same slug '
                f'and different training slug.\n Original error: {err}'
            )
        self.assertEqual(page_1.slug, page_2.slug)

    def test_cannot_create_pages_with_same_slug_and_training_slug(self):
        with self.assertRaises(IntegrityError):
            TrainingFlatPage.objects.create(**self.flatpage_data)
            TrainingFlatPage.objects.create(**self.flatpage_data)

    def test_content_html_updated_on_save(self):
        page = TrainingFlatPage.objects.create(**self.flatpage_data)
        self.assertHTMLEqual(page.content_html, '<h1>hello world</h1>')
        page.content = '## Updated content'
        page.save()
        self.assertHTMLEqual(page.content_html, '<h2>Updated content</h2>')


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestTrainingFlatPage(TestCase):
    def setUp(self) -> None:
        self.training_slug = 'scripting-for-artists'
        self.page_slug = 'blender-28'
        self.content = '## A very specific flat page'
        self.training = TrainingFactory(slug=self.training_slug, is_published=True)
        self.page = TrainingFlatPageFactory(
            training=self.training, slug=self.page_slug, content=self.content
        )

    def test_flatpage_endpoint(self):
        page_url = reverse(
            'training-flatpage',
            kwargs={'training_slug': self.training_slug, 'page_slug': self.page_slug},
        )
        with self.assertTemplateUsed('training/flatpage.html'):
            response = self.client.get(page_url)

            self.assertEqual(response.status_code, 200)
            self.assertInHTML(
                '<h2>A very specific flat page</h2>', response.content.decode('utf-8')
            )
