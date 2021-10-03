from django.test import TestCase
from django.urls import reverse

from common.tests.factories.films import FilmFactory
from common.tests.factories.users import UserFactory
from films.models import Film, FilmProductionCredit


class TestProductionCredit(TestCase):
    def setUp(self) -> None:
        self.film: Film = FilmFactory()
        self.user = UserFactory()

    def test_film_production_credit_model(self):
        """Assign credit to user and check if stored correctly."""

        FilmProductionCredit.objects.create(user=self.user, film=self.film)

        self.assertEqual(1, self.user.production_credits.count())
        # Ensure that is_public is None by default
        credit = self.user.production_credits.get(film=self.film)
        self.assertEqual(None, credit.is_public)

    def test_user_production_credit_endpoint(self):
        page_url = reverse('production-credit', kwargs={'film_slug': self.film.slug})
        response = self.client.get(page_url)
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.user)
        # with self.assertTemplateUsed('films/production_credit.html'):

        # Ensure 404 if user has no credit on the film
        response = self.client.get(page_url)
        self.assertEqual(response.status_code, 404)

        FilmProductionCredit.objects.create(user=self.user, film=self.film)
        with self.assertTemplateUsed('films/production_credit.html'):
            response = self.client.get(page_url)
            self.assertEqual(response.status_code, 200)
