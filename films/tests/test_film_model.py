from django.test import TestCase
from unittest.mock import patch, call

from common.tests.factories.films import FilmFactory
from common.tests.factories.users import UserFactory
from films.models import Film


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

    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_film_storage_urls(self, mock_storage_url):
        """Tests for the Film image assets.

        Create a new film and check that the right storage is called when its image URLs are accessed.
        """
        film: Film = FilmFactory()

        self.assertEqual(film.logo.url, 's3://file')
        self.assertEqual(film.poster.url, 's3://file')
        self.assertEqual(film.picture_header.url, 's3://file')
        self.assertEqual(film.thumbnail.url, 's3://file')

        mock_storage_url.assert_has_calls(
            (
                call(film.logo.name,),
                call(film.poster.name,),
                call(film.picture_header.name,),
                call(film.thumbnail.name,),
            )
        )
