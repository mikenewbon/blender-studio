from unittest.mock import patch

from django.test import TestCase
from django.urls.base import reverse

from common.factories.films import FilmFactory, CollectionFactory, AssetFactory
from films.views.api.assets import SiteContexts


class TestSiteContextResolution(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.asset = AssetFactory()
        cls.other_asset = AssetFactory(film=cls.asset.film, collection=cls.asset.collection)

    @patch('films.views.api.assets.get_next_asset_in_gallery', return_value=AssetFactory())
    @patch('films.views.api.assets.get_previous_asset_in_gallery', return_value=AssetFactory())
    def test_gallery_site_context(self, get_previous_asset_mock, get_next_asset_mock):
        query_string = f'site_context={SiteContexts.GALLERY.value}'
        response = self.client.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')

        self.assertEqual(response.status_code, 200)
        get_previous_asset_mock.assert_called_once_with(self.asset)
        get_next_asset_mock.assert_called_once_with(self.asset)

    @patch('films.views.api.assets.get_next_asset_in_featured_artwork', return_value=AssetFactory())
    @patch(
        'films.views.api.assets.get_previous_asset_in_featured_artwork', return_value=AssetFactory()
    )
    def test_featured_artwork_site_context(self, get_previous_asset_mock, get_next_asset_mock):
        query_string = f'site_context={SiteContexts.FEATURED_ARTWORK.value}'
        response = self.client.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')

        self.assertEqual(response.status_code, 200)
        get_previous_asset_mock.assert_called_once_with(self.asset)
        get_next_asset_mock.assert_called_once_with(self.asset)

    @patch('films.views.api.assets.get_next_asset_in_weeklies', return_value=AssetFactory())
    @patch('films.views.api.assets.get_previous_asset_in_weeklies', return_value=AssetFactory())
    def test_weeklies_site_context(self, get_previous_asset_mock, get_next_asset_mock):
        query_string = f'site_context={SiteContexts.WEEKLIES.value}'
        response = self.client.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')

        self.assertEqual(response.status_code, 200)
        get_previous_asset_mock.assert_called_once_with(self.asset)
        get_next_asset_mock.assert_called_once_with(self.asset)

    def test_wrong_site_context(self):
        query_string = 'site_context=definitely-incorrect'
        response = self.client.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('asset'), self.asset)
        self.assertEqual(response.context.get('previous_asset'), None)
        self.assertEqual(response.context.get('next_asset'), None)

    def test_no_site_context_in_query_string(self):
        response = self.client.get(reverse("api-asset", args=(self.asset.pk,)))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('asset'), self.asset)
        self.assertEqual(response.context.get('previous_asset'), None)
        self.assertEqual(response.context.get('next_asset'), None)


class TestAssetOrderingInGallery(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.site_context = SiteContexts.GALLERY.value

        film = FilmFactory()
        cls.collection_a = CollectionFactory(film=film)
        collection_b = CollectionFactory(film=film, order=1)
        collection_c = CollectionFactory(film=film, order=2)

        other_film = FilmFactory()
        other_collection = CollectionFactory(film=other_film)

        # assets from collection A: should be sorted by (order, date_created)
        cls.asset_a_2 = AssetFactory(
            film=film, collection=cls.collection_a, order=2, is_featured=True
        )
        cls.asset_a_3 = AssetFactory(film=film, collection=cls.collection_a)
        cls.asset_a_0 = AssetFactory(film=film, collection=cls.collection_a, order=1)
        cls.asset_a_1 = AssetFactory(film=film, collection=cls.collection_a, order=1)

        # assets from other films and collections, should not be included in context:
        asset_b_0 = AssetFactory(film=film, collection=collection_b, is_featured=True)
        asset_c_0 = AssetFactory(film=film, collection=collection_c, is_featured=True)
        other_asset_0 = AssetFactory(film=other_film, collection=other_collection)
        other_asset_1 = AssetFactory(film=other_film, collection=other_collection, is_featured=True)

    def test_previous_asset_for_first_asset_is_none(self):
        first_asset = self.asset_a_0
        response = self.client.get(
            f'{reverse("api-asset", args=(first_asset.pk,))}?site_context={self.site_context}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('asset'), first_asset)
        self.assertEqual(response.context.get('previous_asset'), None)

    def test_next_asset_for_last_asset_is_none(self):
        last_asset = self.asset_a_3
        response = self.client.get(
            f'{reverse("api-asset", args=(last_asset.pk,))}?site_context={self.site_context}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('asset'), last_asset)
        self.assertEqual(response.context.get('next_asset'), None)

    def test_assets_from_collection_sorted_by_order_and_date_created(self):
        assets = [self.asset_a_0, self.asset_a_1, self.asset_a_2, self.asset_a_3]

        for previous_asset, asset, next_asset in zip(assets, assets[1:], assets[2:]):
            response = self.client.get(
                f'{reverse("api-asset", args=(asset.pk,))}?site_context={self.site_context}'
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context.get('previous_asset'), previous_asset)
            self.assertEqual(response.context.get('asset'), asset)
            self.assertEqual(response.context.get('next_asset'), next_asset)


class TestAssetOrderingInFeaturedArtwork(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.site_context = SiteContexts.FEATURED_ARTWORK.value

        film = FilmFactory()
        collection_a = CollectionFactory(film=film)
        collection_b = CollectionFactory(film=film, order=1)
        collection_c = CollectionFactory(film=film, order=2)

        other_film = FilmFactory()
        other_collection = CollectionFactory(film=other_film)

        # all the featured assets from the film should be sorted by date_created:
        cls.featured_asset_0 = AssetFactory(
            film=film, collection=collection_a, order=2, is_featured=True
        )
        asset_a_0 = AssetFactory(film=film, collection=collection_a, order=1)
        asset_a_1 = AssetFactory(film=film, collection=collection_a, order=2)
        cls.featured_asset_1 = AssetFactory(film=film, collection=collection_b, is_featured=True)
        cls.featured_asset_2 = AssetFactory(film=film, collection=collection_c, is_featured=True)
        asset_a_2 = AssetFactory(film=film, collection=collection_a, order=3)
        cls.featured_asset_3 = AssetFactory(film=film, collection=collection_a, is_featured=True)

        # assets from the other film should not be included in context:
        other_asset_0 = AssetFactory(film=other_film, collection=other_collection)
        other_asset_1 = AssetFactory(film=other_film, collection=other_collection, is_featured=True)

    def test_previous_asset_for_first_asset_is_none(self):
        first_asset = self.featured_asset_0
        response = self.client.get(
            f'{reverse("api-asset", args=(first_asset.pk,))}?site_context={self.site_context}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('asset'), first_asset)
        self.assertEqual(response.context.get('previous_asset'), None)

    def test_next_asset_for_last_asset_is_none(self):
        last_asset = self.featured_asset_3
        response = self.client.get(
            f'{reverse("api-asset", args=(last_asset.pk,))}?site_context={self.site_context}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('asset'), last_asset)
        self.assertEqual(response.context.get('next_asset'), None)

    def test_featured_assets_sorted_by_date_created(self):
        assets = [
            self.featured_asset_0,
            self.featured_asset_1,
            self.featured_asset_2,
            self.featured_asset_3,
        ]
        for previous_asset, asset, next_asset in zip(assets, assets[1:], assets[2:]):
            response = self.client.get(
                f'{reverse("api-asset", args=(asset.pk,))}?site_context={self.site_context}'
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context.get('previous_asset'), previous_asset)
            self.assertEqual(response.context.get('asset'), asset)
            self.assertEqual(response.context.get('next_asset'), next_asset)
