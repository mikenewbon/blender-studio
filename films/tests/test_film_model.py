from django.test import TestCase

from common.tests.factories.films import FilmFactory
from films.models import Film

from common.tests.factories.users import UserFactory


class TestFilmModel(TestCase):
    def test_film_create_with_crew_member(self):
        """Tests for the FilmCrew model.

        Create a new film, assign a new user with an 'Artist' role and
        ensure that it's available as part of film.filmcrew_set
        """

        expected_role = 'Artist'
        film: Film = FilmFactory()
        author_a = UserFactory()
        film.crew.add(author_a, through_defaults={'role': expected_role})
        self.assertIn(author_a, film.crew.all())
        self.assertEqual(expected_role, film.filmcrew_set.get(user=author_a).role)
