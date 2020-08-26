import factory
from factory.django import DjangoModelFactory

from blog.models import PostComment
from comments.models import Comment
from common.tests.factories.blog import PostFactory
from common.tests.factories.users import UserFactory
from search import signals as search_signals


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = Comment

    user = factory.SubFactory(UserFactory)
    message = factory.Faker('sentence')


@factory.django.mute_signals(search_signals.post_save)
class PostCommentFactory(DjangoModelFactory):
    class Meta:
        model = PostComment

    post = factory.SubFactory(PostFactory)
    comment = factory.SubFactory(CommentFactory)


class CommentUnderPostFactory(CommentFactory):
    comment_post = factory.RelatedFactory(PostCommentFactory, factory_related_name='comment')
