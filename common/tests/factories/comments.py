import factory

from comments.models import Comment
from common.tests.factories.users import UserFactory


class CommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Comment

    user = factory.SubFactory(UserFactory)
    message = factory.Faker('sentence')
