from django.db.utils import IntegrityError
from django.test.testcases import TestCase
from django.urls import reverse

from common.tests.factories.films import FilmFactory, FilmFlatPageFactory
from films.models import FilmFlatPage


class TestFilmFlatPageModel(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.film_1 = FilmFactory()
        cls.film_2 = FilmFactory()
        cls.flatpage_data = {'film': cls.film_1, 'title': 'About', 'content': '# hello world'}

    def test_slug_and_content_html_created_on_save(self):
        flatpage = FilmFlatPage.objects.create(
            film=self.film_1, title='New Page', content='# hello world'
        )
        self.assertEqual(flatpage.slug, 'new-page')
        self.assertHTMLEqual(flatpage.content_html, '<h1>hello world</h1>')

    def test_slug_created_only_if_not_provided(self):
        custom_slug = 'custom'
        flatpage = FilmFlatPage.objects.create(
            film=self.film_1, title='New Page', slug=custom_slug, content='# hello world'
        )
        self.assertEqual(flatpage.slug, custom_slug)

    def test_create_pages_with_same_slugs_for_different_films(self):
        assert self.film_1.slug != self.film_2.slug
        try:
            page_1 = FilmFlatPage.objects.create(
                film=self.film_1, title='New Page', content='# hello world'
            )
            page_2 = FilmFlatPage.objects.create(
                film=self.film_2, title='New Page', content='# hello world'
            )
        except IntegrityError as err:
            self.fail(
                f'It should be possible to create flat pages with the same slug '
                f'and different film slug.\n Original error: {err}'
            )
        self.assertEqual(page_1.slug, page_2.slug)

    def test_cannot_create_pages_with_same_slug_and_film_slug(self):
        with self.assertRaises(IntegrityError):
            FilmFlatPage.objects.create(**self.flatpage_data)
            FilmFlatPage.objects.create(**self.flatpage_data)

    def test_content_html_updated_on_save(self):
        page = FilmFlatPage.objects.create(**self.flatpage_data)
        self.assertHTMLEqual(page.content_html, '<h1>hello world</h1>')
        page.content = '## Updated content'
        page.save()
        self.assertHTMLEqual(page.content_html, '<h2>Updated content</h2>')


class TestFilmFlatPage(TestCase):
    def setUp(self) -> None:
        self.film_slug = 'coffee-run'
        self.page_slug = 'about'
        self.content = '## A very specific flat page'
        self.film = FilmFactory(slug=self.film_slug)
        self.page = FilmFlatPageFactory(film=self.film, slug=self.page_slug, content=self.content)

    def test_flatpage_endpoint(self):
        page_url = reverse(
            'film-flatpage', kwargs={'film_slug': self.film_slug, 'page_slug': self.page_slug}
        )
        with self.assertTemplateUsed('films/flatpage.html'):
            response = self.client.get(page_url)

            self.assertEqual(response.status_code, 200)
            self.assertInHTML(
                '<h2>A very specific flat page</h2>', response.content.decode('utf-8')
            )
