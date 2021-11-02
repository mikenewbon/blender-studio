from django.test import TestCase, override_settings

from looper.tests.test_preferred_currency import EURO_IPV4, USA_IPV4

from common.tests.factories.characters import CharacterVersionFactory, CharacterShowcaseFactory
from common.tests.factories.users import UserFactory
from stats.models import StaticAssetView


@override_settings(
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    PUBLIC_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
)
class TestCharacterVersion(TestCase):
    def test_get_records_a_static_asset_view(self):
        version = CharacterVersionFactory(is_published=True, character__is_published=True)
        self.assertEqual(0, StaticAssetView.objects.count())
        url = version.get_absolute_url()

        # "View" the character version anonymously
        response = self.client.get(url, REMOTE_ADDR=USA_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(1, StaticAssetView.objects.count())
        view = StaticAssetView.objects.first()
        self.assertEqual(view.static_asset_id, version.static_asset_id)
        self.assertEqual(view.ip_address, USA_IPV4)
        self.assertIsNone(view.user_id)

        # "View" the character version anonymously again, from the same IP
        response = self.client.get(url, REMOTE_ADDR=USA_IPV4)

        # No new records should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(
            1, StaticAssetView.objects.count(), [_ for _ in StaticAssetView.objects.all()]
        )

        # "View" the character version anonymously, from another IP
        response = self.client.get(url, REMOTE_ADDR=EURO_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(2, StaticAssetView.objects.count())
        self.assertEqual(
            StaticAssetView.objects.get(ip_address=EURO_IPV4).static_asset_id,
            version.static_asset_id,
        )

        # "View" the character version as logged in user, IP doesn't matter
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(url, REMOTE_ADDR=EURO_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(3, StaticAssetView.objects.count())
        self.assertEqual(
            StaticAssetView.objects.get(user_id=user.pk).static_asset_id, version.static_asset_id
        )

        # "View" the character version as logged in user, same user, IP doesn't matter
        self.client.force_login(user)
        response = self.client.get(url, REMOTE_ADDR=USA_IPV4)

        # No new records should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(3, StaticAssetView.objects.count())

        # "View" the character version as logged in user, different user, IP doesn't matter
        another_user = UserFactory()
        self.client.force_login(another_user)
        response = self.client.get(url, REMOTE_ADDR=EURO_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(4, StaticAssetView.objects.count())
        self.assertEqual(
            StaticAssetView.objects.get(user_id=another_user.pk).static_asset_id,
            version.static_asset_id,
        )


@override_settings(
    DEFAULT_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
    PUBLIC_FILE_STORAGE='django.core.files.storage.FileSystemStorage',
)
class TestCharacterShowcase(TestCase):
    def test_get_records_a_static_asset_view(self):
        showcase = CharacterShowcaseFactory(is_published=True, character__is_published=True)
        self.assertEqual(0, StaticAssetView.objects.count())
        url = showcase.get_absolute_url()

        # "View" the character showcase anonymously
        response = self.client.get(url, REMOTE_ADDR=USA_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(1, StaticAssetView.objects.count())
        view = StaticAssetView.objects.first()
        self.assertEqual(view.static_asset_id, showcase.static_asset_id)
        self.assertEqual(view.ip_address, USA_IPV4)
        self.assertIsNone(view.user_id)

        # "View" the character showcase anonymously again, from the same IP
        response = self.client.get(url, REMOTE_ADDR=USA_IPV4)

        # No new records should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(
            1, StaticAssetView.objects.count(), [_ for _ in StaticAssetView.objects.all()]
        )

        # "View" the character showcase anonymously, from another IP
        response = self.client.get(url, REMOTE_ADDR=EURO_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(2, StaticAssetView.objects.count())
        self.assertEqual(
            StaticAssetView.objects.get(ip_address=EURO_IPV4).static_asset_id,
            showcase.static_asset_id,
        )

        # "View" the character showcase as logged in user, IP doesn't matter
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(url, REMOTE_ADDR=EURO_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(3, StaticAssetView.objects.count())
        self.assertEqual(
            StaticAssetView.objects.get(user_id=user.pk).static_asset_id, showcase.static_asset_id
        )

        # "View" the character showcase as logged in user, same user, IP doesn't matter
        self.client.force_login(user)
        response = self.client.get(url, REMOTE_ADDR=USA_IPV4)

        # No new records should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(3, StaticAssetView.objects.count())

        # "View" the character showcase as logged in user, different user, IP doesn't matter
        another_user = UserFactory()
        self.client.force_login(another_user)
        response = self.client.get(url, REMOTE_ADDR=EURO_IPV4)

        # A record of this view should be created
        self.assertEqual(200, response.status_code, 200)
        self.assertEqual(4, StaticAssetView.objects.count())
        self.assertEqual(
            StaticAssetView.objects.get(user_id=another_user.pk).static_asset_id,
            showcase.static_asset_id,
        )
