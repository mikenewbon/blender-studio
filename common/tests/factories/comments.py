import factory
from factory.django import DjangoModelFactory

from comments.models import Comment
from common.tests.factories.users import UserFactory


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = Comment

    user = factory.SubFactory(UserFactory)
    message = factory.Faker('sentence')
