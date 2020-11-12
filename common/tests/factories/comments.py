import factory
from factory.django import DjangoModelFactory

from blog.models import PostComment
from comments import signals as comments_signals
from comments.models import Comment
from common.tests.factories.blog import PostFactory
from common.tests.factories.films import AssetFactory
from common.tests.factories.training import SectionFactory
from common.tests.factories.users import UserFactory
from films.models.assets import AssetComment
from search import signals as search_signals
from training.models.sections import SectionComment


@factory.django.mute_signals(comments_signals.post_save)
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


@factory.django.mute_signals(search_signals.post_save)
class AssetCommentFactory(DjangoModelFactory):
    class Meta:
        model = AssetComment

    asset = factory.SubFactory(AssetFactory)
    comment = factory.SubFactory(CommentFactory)


class CommentUnderAssetFactory(CommentFactory):
    comment_asset = factory.RelatedFactory(AssetCommentFactory, factory_related_name='comment')


@factory.django.mute_signals(search_signals.post_save)
class SectionCommentFactory(DjangoModelFactory):
    class Meta:
        model = SectionComment

    section = factory.SubFactory(SectionFactory)
    comment = factory.SubFactory(CommentFactory)


class CommentUnderSectionFactory(CommentFactory):
    comment_section = factory.RelatedFactory(SectionCommentFactory, factory_related_name='comment')
