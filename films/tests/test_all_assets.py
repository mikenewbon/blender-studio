from django.test import TestCase
from django.urls import reverse

from common.tests.factories.films import FilmFactory
from common.tests.factories.users import UserFactory


class TestAllAssets(TestCase):
    maxDiff = None

    def setUp(self):
        self.film = FilmFactory()
        self.url = reverse('film-all-assets', kwargs={'film_slug': self.film.slug})

    def test_view_not_logged_in(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_view_logged_in(self):
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
