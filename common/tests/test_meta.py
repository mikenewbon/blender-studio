from unittest.mock import patch, PropertyMock
import re

from django.test.testcases import TestCase
from django.urls import reverse

from common.tests.factories.blog import PostFactory
from common.tests.factories.films import FilmFactory, AssetFactory
from common.tests.factories.static_assets import StaticAssetFactory
from common.tests.factories.users import UserFactory

shared_meta = {
    'name=.author.': 'Blender Institute',
    'property=.og:site_name.': 'Blender Studio',
    'property=.og:type.': 'website',
    'property=.og:locale.': 'en_US',
    'name=.twitter:card.': 'summary_large_image',
    'name=.twitter:site.': '@Blender_Cloud',
}


class TestSiteMetadata(TestCase):
    def setUp(self):
        super().setUp()
        # Patch away all thumbnailing and S3 storage
        for patcher in [
            patch('botocore.client.ClientCreator'),
            patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail'),
            patch(
                'films.models.films.Film.thumbnail_m_url',
                PropertyMock(return_value='https://film/thumbnail_m.jpg'),
            ),
            patch(
                'blog.models.Post.thumbnail_m_url',
                PropertyMock(return_value='https://post/thumbnail_m.jpg'),
            ),
            patch(
                'static_assets.models.static_assets.StaticAsset.thumbnail_m_url',
                PropertyMock(return_value='https://static/asset/thumbnail_m.jpg'),
            ),
        ]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _find_link(self, html: bytes):
        found_link = re.findall(
            r'<link\s+rel=.canonical.\s+href="([^"]+)"\s*/>',
            html.decode(),
            re.MULTILINE,
        )
        self.assertIsNotNone(found_link, 'Unable to find <link rel="canonical" .. />')
        if found_link:
            self.assertEqual(len(found_link), 1, f'Multiple link tags found: {found_link}')
            return found_link[0]

    def _find_meta(self, html: bytes, prop: str):
        found_meta = re.findall(
            fr'<meta\s+{prop}(?:[\s\n\r]*)content="([^"]+)"(?:[\s\n\r]*)>',
            html.decode(),
            re.MULTILINE,
        )
        self.assertIsNotNone(found_meta, f'Unable to find {prop} meta')
        if found_meta:
            self.assertEqual(len(found_meta), 1, f'Multiple meta {prop} found: {found_meta}')
            return found_meta[0]

    def assertMetaEquals(self, html: bytes, prop: str, value: str):
        self.assertEqual(self._find_meta(html, prop), value, prop)

    def assertCanonicalLinkEquals(self, html: bytes, value: str):
        self.assertEqual(self._find_link(html), value)

    def test_homepage(self):
        # Login to avoid being redirected to the welcome page
        user = UserFactory()
        self.client.force_login(user)
        page_url = reverse('home')

        response = self.client.get(page_url + '?foo=bar&should=not&affect=canonical&url=true')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(html, 'http://testserver/')
        for meta, value in {
            'property=.og:url.': 'http://testserver/',
            **shared_meta,
            'property=.og:title.': 'Blender Studio',
            'name=.twitter:title.': 'Blender Studio',
            'property=.og:description.': 'Blender Studio is a web based service developed by Blender Institute that allows people to access the training videos and all the data from the open projects.',
            'name=.twitter:description.': 'Blender Studio is a web based service developed by Blender Institute that allows people to access the training videos and all the data from the open projects.',
            'property=.og:image.': 'http://testserver/static/common/images/blender-studio-og.jpg',
            'name=.twitter:image.': 'http://testserver/static/common/images/blender-studio-og.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_welcome(self):
        page_url = reverse('welcome')

        response = self.client.get(page_url + '?foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(html, 'http://testserver/welcome/')
        for meta, value in {
            'property=.og:url.': 'http://testserver/welcome/',
            **shared_meta,
            'property=.og:title.': 'Blender Studio',
            'name=.twitter:title.': 'Blender Studio',
            'property=.og:description.': 'Blender Studio is a web based service developed by Blender Institute that allows people to access the training videos and all the data from the open projects.',
            'name=.twitter:description.': 'Blender Studio is a web based service developed by Blender Institute that allows people to access the training videos and all the data from the open projects.',
            'property=.og:image.': 'http://testserver/static/common/images/blender-studio-og.jpg',
            'name=.twitter:image.': 'http://testserver/static/common/images/blender-studio-og.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        page_url = reverse('film-detail', kwargs={'film_slug': film_slug})

        response = self.client.get(page_url + '?foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(html, f'http://testserver/films/{film_slug}/')
        for meta, value in {
            'property=.og:url.': f'http://testserver/films/{film_slug}/',
            **shared_meta,
            'property=.og:title.': f'{film.title} - Blender Studio',
            'name=.twitter:title.': f'{film.title} - Blender Studio',
            'property=.og:description.': film.description,
            'name=.twitter:description.': film.description,
            'property=.og:image.': 'https://film/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://film/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film_non_featured_asset_links_asset_in_collection(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        asset = AssetFactory(film=film, static_asset=StaticAssetFactory())
        page_url = reverse('film-detail', kwargs={'film_slug': film_slug})

        response = self.client.get(page_url + f'?asset={asset.pk}&foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(
            html,
            f'http://testserver{asset.collection.url}?asset={asset.pk}',
        )
        for meta, value in {
            'property=.og:url.': f'http://testserver{asset.collection.url}?asset={asset.pk}',
            **shared_meta,
            'property=.og:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'name=.twitter:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'property=.og:description.': asset.description,
            'name=.twitter:description.': asset.description,
            'property=.og:image.': 'https://static/asset/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://static/asset/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film_featured_asset_links_to_film_gallery_page(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        asset = AssetFactory(film=film, is_featured=True, static_asset=StaticAssetFactory())

        self.assertEqual(asset.url, f'/films/coffee-run/gallery/?asset={asset.pk}')
        response = self.client.get(f'http://testserver{asset.url}&foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(
            html, f'http://testserver/films/{film_slug}/gallery/?asset={asset.pk}'
        )
        for meta, value in {
            'property=.og:url.': f'http://testserver/films/{film_slug}/gallery/?asset={asset.pk}',
            **shared_meta,
            'property=.og:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'name=.twitter:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'property=.og:description.': asset.description,
            'name=.twitter:description.': asset.description,
            'property=.og:image.': 'https://static/asset/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://static/asset/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film_gallery(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        page_url = reverse('film-gallery', kwargs={'film_slug': film_slug})

        response = self.client.get(page_url + '?foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(html, f'http://testserver/films/{film_slug}/gallery/')
        for meta, value in {
            'property=.og:url.': f'http://testserver/films/{film_slug}/gallery/',
            **shared_meta,
            'property=.og:title.': f'{film.title} - Featured Artwork - Blender Studio',
            'name=.twitter:title.': f'{film.title} - Featured Artwork - Blender Studio',
            'property=.og:description.': film.description,
            'name=.twitter:description.': film.description,
            'property=.og:image.': 'https://film/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://film/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film_gallery_asset(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        asset = AssetFactory(film=film, static_asset=StaticAssetFactory())
        page_url = reverse('film-gallery', kwargs={'film_slug': film_slug})

        response = self.client.get(page_url + f'?asset={asset.pk}&foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(
            html,
            f'http://testserver/films/{film_slug}/{asset.collection.slug}/?asset={asset.pk}',
        )
        for meta, value in {
            'property=.og:url.': f'http://testserver/films/{film_slug}/{asset.collection.slug}/?asset={asset.pk}',
            **shared_meta,
            'property=.og:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'name=.twitter:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'property=.og:description.': asset.description,
            'name=.twitter:description.': asset.description,
            'property=.og:image.': 'https://static/asset/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://static/asset/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film_gallery_collection(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        asset = AssetFactory(film=film, static_asset=StaticAssetFactory())
        page_url = reverse(
            'collection-detail',
            kwargs={
                'film_slug': film_slug,
                'collection_slug': asset.collection.slug,
            },
        )

        response = self.client.get(page_url + '?foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(
            html,
            f'http://testserver/films/{film_slug}/{asset.collection.slug}/',
        )
        for meta, value in {
            'property=.og:url.': f'http://testserver/films/{film_slug}/{asset.collection.slug}/',
            **shared_meta,
            'property=.og:title.': f'{film.title} - {asset.collection.name} - Blender Studio',
            'name=.twitter:title.': f'{film.title} - {asset.collection.name} - Blender Studio',
            'property=.og:description.': asset.collection.text,
            'name=.twitter:description.': asset.collection.text,
            'property=.og:image.': 'https://film/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://film/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film_gallery_collection_empty_text_and_name(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        asset = AssetFactory(
            film=film,
            static_asset=StaticAssetFactory(),
            collection__text='',
            collection__name='',
        )
        page_url = reverse(
            'collection-detail',
            kwargs={
                'film_slug': film_slug,
                'collection_slug': asset.collection.slug,
            },
        )

        response = self.client.get(page_url + '?foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(
            html,
            f'http://testserver/films/{film_slug}/{asset.collection.slug}/',
        )
        for meta, value in {
            'property=.og:url.': f'http://testserver/films/{film_slug}/{asset.collection.slug}/',
            **shared_meta,
            'property=.og:title.': f'{film.title} - {asset.collection.name} - Blender Studio',
            'name=.twitter:title.': f'{film.title} - {asset.collection.name} - Blender Studio',
            'property=.og:description.': film.description,
            'name=.twitter:description.': film.description,
            'property=.og:image.': 'https://film/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://film/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_film_gallery_collection_asset(self):
        film_slug = 'coffee-run'
        film = FilmFactory(slug=film_slug)
        asset = AssetFactory(film=film, static_asset=StaticAssetFactory())
        page_url = reverse(
            'collection-detail',
            kwargs={
                'film_slug': film_slug,
                'collection_slug': asset.collection.slug,
            },
        )

        response = self.client.get(page_url + f'?asset={asset.pk}&foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(
            html,
            f'http://testserver/films/{film_slug}/{asset.collection.slug}/?asset={asset.pk}',
        )
        for meta, value in {
            'property=.og:url.': f'http://testserver/films/{film_slug}/{asset.collection.slug}/?asset={asset.pk}',
            **shared_meta,
            'property=.og:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'name=.twitter:title.': f'{film.title} - {asset.collection.name}: {asset.name} - Blender Studio',
            'property=.og:description.': asset.description,
            'name=.twitter:description.': asset.description,
            'property=.og:image.': 'https://static/asset/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://static/asset/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)

    def test_blog_post(self):
        post = PostFactory()
        page_url = reverse('post-detail', kwargs={'slug': post.slug})

        response = self.client.get(page_url + '?foo=bar')

        self.assertEqual(response.status_code, 200)
        html = response.content

        self.assertCanonicalLinkEquals(
            html,
            f'http://testserver/blog/{post.slug}/',
        )
        for meta, value in {
            'property=.og:url.': f'http://testserver/blog/{post.slug}/',
            **shared_meta,
            'property=.og:title.': f'{post.title} - Blender Studio',
            'name=.twitter:title.': f'{post.title} - Blender Studio',
            'property=.og:description.': post.excerpt,
            'name=.twitter:description.': post.excerpt,
            'property=.og:image.': 'https://post/thumbnail_m.jpg',
            'name=.twitter:image.': 'https://post/thumbnail_m.jpg',
        }.items():
            self.assertMetaEquals(html, meta, value)
