from django.test import TestCase


class TestSiteContextResolution(TestCase):
    def test_gallery_site_context(self):
        pass

    def test_featured_artwork_site_context(self):
        pass

    def test_weeklies_site_context(self):
        pass

    def test_wrong_site_context(self):
        site_context = 'definitely incorrect'

    def test_no_site_context_in_query_string(self):
        pass


class TestAssetOrderingInGallery(TestCase):
    def setUpTestData(cls) -> None:
        pass

    def test_previous_asset_for_first_asset_is_the_last_one(self):
        pass

    def test_next_asset_for_last_asset_is_the_first_one(self):
        pass
