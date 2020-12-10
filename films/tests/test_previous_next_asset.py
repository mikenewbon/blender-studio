import datetime as dt
from unittest.mock import patch

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls.base import reverse

from common.tests.factories.films import (
    FilmFactory,
    CollectionFactory,
    AssetFactory,
    ProductionLogFactory,
    ProductionLogEntryFactory,
    ProductionLogEntryAssetFactory,
)
from common.tests.factories.static_assets import StaticAssetFactory
from common.tests.factories.users import UserFactory
from films.queries import SiteContexts, get_asset_context


class TestSiteContextResolution(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.factory = RequestFactory()
        cls.user = UserFactory()

        cls.asset = AssetFactory()
        cls.other_asset = AssetFactory(film=cls.asset.film, collection=cls.asset.collection)

    @patch('films.queries.get_next_asset_in_gallery', return_value=None)
    @patch('films.queries.get_previous_asset_in_gallery', return_value=None)
    def test_gallery_site_context(self, get_previous_asset_mock, get_next_asset_mock):
        query_string = f'site_context={SiteContexts.GALLERY.value}'
        request = self.factory.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')
        request.user = self.user
        _ = get_asset_context(self.asset, request)

        get_previous_asset_mock.assert_called_once_with(self.asset)
        get_next_asset_mock.assert_called_once_with(self.asset)

    @patch('films.queries.get_next_asset_in_featured_artwork', return_value=None)
    @patch('films.queries.get_previous_asset_in_featured_artwork', return_value=None)
    def test_featured_artwork_site_context(self, get_previous_asset_mock, get_next_asset_mock):
        query_string = f'site_context={SiteContexts.FEATURED_ARTWORK.value}'
        request = self.factory.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')
        request.user = self.user
        _ = get_asset_context(self.asset, request)

        get_previous_asset_mock.assert_called_once_with(self.asset)
        get_next_asset_mock.assert_called_once_with(self.asset)

    @patch('films.queries.get_next_asset_in_production_logs', return_value=None)
    @patch('films.queries.get_previous_asset_in_production_logs', return_value=None)
    def test_production_logs_site_context(self, get_previous_asset_mock, get_next_asset_mock):
        query_string = f'site_context={SiteContexts.PRODUCTION_LOGS.value}'
        request = self.factory.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')
        request.user = self.user
        _ = get_asset_context(self.asset, request)

        get_previous_asset_mock.assert_called_once_with(self.asset)
        get_next_asset_mock.assert_called_once_with(self.asset)

    def test_wrong_site_context(self):
        query_string = 'site_context=definitely-incorrect'
        request = self.factory.get(f'{reverse("api-asset", args=(self.asset.pk,))}?{query_string}')
        request.user = self.user
        context = get_asset_context(self.asset, request)

        self.assertEqual(context['asset'], self.asset)
        self.assertEqual(context['previous_asset'], None)
        self.assertEqual(context['next_asset'], None)

    def test_no_site_context_in_query_string(self):
        request = self.factory.get(reverse("api-asset", args=(self.asset.pk,)))
        request.user = self.user
        context = get_asset_context(self.asset, request)

        self.assertEqual(context['asset'], self.asset)
        self.assertEqual(context['previous_asset'], None)
        self.assertEqual(context['next_asset'], None)


class TestAssetOrderingInGallery(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.site_context = SiteContexts.GALLERY.value
        cls.factory = RequestFactory()
        cls.user = UserFactory()

        film = FilmFactory()
        cls.collection_a = CollectionFactory(film=film)
        collection_b = CollectionFactory(film=film, order=1)
        collection_c = CollectionFactory(film=film, order=2)

        other_film = FilmFactory()
        other_collection = CollectionFactory(film=other_film)

        # Assets from collection A: should be sorted by (order, name)
        cls.asset_a_2 = AssetFactory(
            film=film, collection=cls.collection_a, order=2, name='Aa', is_featured=True
        )
        cls.asset_a_3 = AssetFactory(film=film, collection=cls.collection_a, name='Aa')
        cls.asset_a_0 = AssetFactory(film=film, collection=cls.collection_a, order=1, name='Bb')
        cls.asset_a_1 = AssetFactory(film=film, collection=cls.collection_a, order=1, name='Cc')

        # Assets from other films and collections, should not be included in context:
        AssetFactory(film=film, collection=collection_b, is_featured=True)
        AssetFactory(film=film, collection=collection_c, is_featured=True)
        AssetFactory(film=other_film, collection=other_collection)
        AssetFactory(film=other_film, collection=other_collection, is_featured=True)

    def test_previous_asset_for_first_asset_is_none(self):
        first_asset = self.asset_a_0
        request = self.factory.get(
            f'{reverse("api-asset", args=(first_asset.pk,))}?site_context={self.site_context}'
        )
        request.user = self.user
        context = get_asset_context(first_asset, request)

        self.assertEqual(context['asset'], first_asset)
        self.assertEqual(context['previous_asset'], None)
        self.assertEqual(context['site_context'], self.site_context)

    def test_next_asset_for_last_asset_is_none(self):
        last_asset = self.asset_a_3
        request = self.factory.get(
            f'{reverse("api-asset", args=(last_asset.pk,))}?site_context={self.site_context}'
        )
        request.user = self.user
        context = get_asset_context(last_asset, request)

        self.assertEqual(context['asset'], last_asset)
        self.assertEqual(context['next_asset'], None)
        self.assertEqual(context['site_context'], self.site_context)

    def test_assets_from_collection_sorted_by_order_and_name(self):
        assets = [self.asset_a_0, self.asset_a_1, self.asset_a_2, self.asset_a_3]

        for previous_asset, asset, next_asset in zip(assets, assets[1:], assets[2:]):
            request = self.factory.get(
                f'{reverse("api-asset", args=(asset.pk,))}?site_context={self.site_context}'
            )
            request.user = self.user
            context = get_asset_context(asset, request)

            self.assertEqual(context['previous_asset'], previous_asset)
            self.assertEqual(context['asset'], asset)
            self.assertEqual(context['next_asset'], next_asset)


class TestAssetOrderingInFeaturedArtwork(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.site_context = SiteContexts.FEATURED_ARTWORK.value
        cls.factory = RequestFactory()
        cls.user = UserFactory()

        film = FilmFactory()
        collection_a = CollectionFactory(film=film)
        collection_b = CollectionFactory(film=film, order=1)
        collection_c = CollectionFactory(film=film, order=2)

        other_film = FilmFactory()
        other_collection = CollectionFactory(film=other_film)

        # All the featured assets from the film should be sorted by date_created:
        cls.featured_asset_0 = AssetFactory(
            film=film, collection=collection_a, order=2, is_featured=True
        )
        AssetFactory(film=film, collection=collection_a, order=1)
        AssetFactory(film=film, collection=collection_a, order=2)
        cls.featured_asset_1 = AssetFactory(film=film, collection=collection_b, is_featured=True)
        cls.featured_asset_2 = AssetFactory(film=film, collection=collection_c, is_featured=True)
        AssetFactory(film=film, collection=collection_a, order=3)
        cls.featured_asset_3 = AssetFactory(film=film, collection=collection_a, is_featured=True)

        # Assets from the other film should not be included in context:
        AssetFactory(film=other_film, collection=other_collection)
        AssetFactory(film=other_film, collection=other_collection, is_featured=True)

    def test_previous_asset_for_first_asset_is_none(self):
        first_asset = self.featured_asset_3  # featured are ordered latest published first
        request = self.factory.get(
            f'{reverse("api-asset", args=(first_asset.pk,))}?site_context={self.site_context}'
        )
        request.user = self.user
        context = get_asset_context(first_asset, request)

        self.assertEqual(context['asset'], first_asset)
        self.assertEqual(context['previous_asset'], None)
        self.assertEqual(context['site_context'], self.site_context)

    def test_next_asset_for_last_asset_is_none(self):
        last_asset = self.featured_asset_0
        request = self.factory.get(
            f'{reverse("api-asset", args=(last_asset.pk,))}?site_context={self.site_context}'
        )
        request.user = self.user
        context = get_asset_context(last_asset, request)

        self.assertEqual(context['asset'], last_asset)
        self.assertEqual(context['next_asset'], None)
        self.assertEqual(context['site_context'], self.site_context)

    def test_featured_assets_sorted_by_date_published(self):
        assets = [
            self.featured_asset_3,
            self.featured_asset_2,
            self.featured_asset_1,
            self.featured_asset_0,
        ]
        for previous_asset, asset, next_asset in zip(assets, assets[1:], assets[2:]):
            request = self.factory.get(
                f'{reverse("api-asset", args=(asset.pk,))}?site_context={self.site_context}'
            )
            request.user = self.user
            context = get_asset_context(asset, request)

            self.assertEqual(context['previous_asset'], previous_asset)
            self.assertEqual(context['asset'], asset)
            self.assertEqual(context['next_asset'], next_asset)


class TestAssetOrderingInProductionLogs(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.site_context = SiteContexts.PRODUCTION_LOGS.value
        cls.factory = RequestFactory()
        cls.user = UserFactory()

        author_a = UserFactory()
        author_b = UserFactory()

        film = FilmFactory()
        log_start_date = dt.date(2020, 6, 1)
        prod_log = ProductionLogFactory(film=film, start_date=log_start_date)
        entry_a = ProductionLogEntryFactory(production_log=prod_log, author=author_a)

        cls.asset_a_0 = AssetFactory(film=film, static_asset=StaticAssetFactory(user=author_a))
        cls.asset_a_1 = AssetFactory(film=film, static_asset=StaticAssetFactory(user=author_a))
        cls.asset_a_2 = AssetFactory(film=film, static_asset=StaticAssetFactory(user=author_a))
        cls.asset_a_3 = AssetFactory(film=film, static_asset=StaticAssetFactory(user=author_a))

        # Author's A assets should be sorted by date_created
        ProductionLogEntryAssetFactory(production_log_entry=entry_a, asset=cls.asset_a_0)
        ProductionLogEntryAssetFactory(production_log_entry=entry_a, asset=cls.asset_a_1)
        ProductionLogEntryAssetFactory(production_log_entry=entry_a, asset=cls.asset_a_2)
        ProductionLogEntryAssetFactory(production_log_entry=entry_a, asset=cls.asset_a_3)

        # Assets from other production log entries should not be included in the context
        other_asset_a = AssetFactory(film=film, static_asset=StaticAssetFactory(user=author_a))
        other_entry = ProductionLogEntryFactory(
            user=author_a, production_log=ProductionLogFactory(start_date=dt.date(1997, 12, 1))
        )
        ProductionLogEntryAssetFactory(production_log_entry=other_entry, asset=other_asset_a)
        asset_b = AssetFactory(film=film, static_asset=StaticAssetFactory(user=author_b))
        entry_b = ProductionLogEntryFactory(production_log=prod_log, author=author_b)
        ProductionLogEntryAssetFactory(production_log_entry=entry_b, asset=asset_b)

    def test_previous_asset_for_first_asset_is_none(self):
        first_asset = self.asset_a_0
        request = self.factory.get(
            f'{reverse("api-asset", args=(first_asset.pk,))}?site_context={self.site_context}'
        )
        request.user = self.user
        context = get_asset_context(first_asset, request)

        self.assertEqual(context['asset'], first_asset)
        self.assertEqual(context['previous_asset'], None)
        self.assertEqual(context['site_context'], self.site_context)

    def test_next_asset_for_last_asset_is_none(self):
        last_asset = self.asset_a_3
        request = self.factory.get(
            f'{reverse("api-asset", args=(last_asset.pk,))}?site_context={self.site_context}'
        )
        request.user = self.user
        context = get_asset_context(last_asset, request)

        self.assertEqual(context['asset'], last_asset)
        self.assertEqual(context['next_asset'], None)
        self.assertEqual(context['site_context'], self.site_context)

    def test_assets_in_production_log_entry_sorted_by_date_created(self):
        assets = [
            self.asset_a_0,
            self.asset_a_1,
            self.asset_a_2,
            self.asset_a_3,
        ]
        for previous_asset, asset, next_asset in zip(assets, assets[1:], assets[2:]):
            request = self.factory.get(
                f'{reverse("api-asset", args=(asset.pk,))}?site_context={self.site_context}'
            )
            request.user = self.user
            context = get_asset_context(asset, request)

            self.assertEqual(context['previous_asset'], previous_asset)
            self.assertEqual(context['asset'], asset)
            self.assertEqual(context['next_asset'], next_asset)
