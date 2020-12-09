from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from common.tests.factories.training import TrainingFactory
from training import context_processors
from training.models import Training
from training.queries.trainings import set_favorite

User = get_user_model()


class ContextProcessorsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_favorited_anonymous_user(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()

        # Create 1 published training
        TrainingFactory(is_published=True)

        context = context_processors.favorited(request)

        self.assertEqual(context, {'favorited_training_ids': []})

    def test_favorited_authenticated_user(self):
        request = self.factory.get('/')
        user = User.objects.create_user(username='john', email='john@…', password='top_secret')
        request.user = user

        # Create 3 published trainings, 2 of them favorited by John
        TrainingFactory(is_published=True)
        training_fav1: Training = TrainingFactory(is_published=True)
        training_fav2: Training = TrainingFactory(is_published=True)
        set_favorite(training_pk=training_fav1.pk, user_pk=user.pk, favorite=True)
        set_favorite(training_pk=training_fav2.pk, user_pk=user.pk, favorite=True)

        context = context_processors.favorited(request)

        self.assertCountEqual(
            context['favorited_training_ids'], [training_fav1.pk, training_fav2.pk]
        )
