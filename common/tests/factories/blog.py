import factory
from factory.django import DjangoModelFactory

from blog.models import Post, Revision
from common.tests.factories.films import FilmFactory
from common.tests.factories.helpers import generate_image_path
from common.tests.factories.users import UserFactory
from search import signals as search_signals


@factory.django.mute_signals(search_signals.post_save)
class PostFactory(DjangoModelFactory):
    class Meta:
        model = Post

    film = factory.SubFactory(FilmFactory)
    author = factory.SubFactory(UserFactory)
    slug = factory.Faker('slug')
    is_published = True


@factory.django.mute_signals(search_signals.post_save)
class RevisionFactory(DjangoModelFactory):
    class Meta:
        model = Revision

    editor = factory.SubFactory(UserFactory)
    title = factory.Faker('text', max_nb_chars=20)
    topic = factory.Faker('text', max_nb_chars=20)
    description = factory.Faker('text', max_nb_chars=50)
    content = factory.Faker('text')
    thumbnail = factory.LazyFunction(generate_image_path)
    is_published = True
    post = factory.SubFactory(PostFactory)
