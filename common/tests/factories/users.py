from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory
import factory

from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken

User = get_user_model()


class OAuthUserInfoFactory(DjangoModelFactory):
    class Meta:
        model = OAuthUserInfo

    oauth_user_id = factory.Sequence(lambda n: n + 899999)

    user = factory.SubFactory('common.tests.factories.users.UserFactory')


class OAuthUserTokenFactory(DjangoModelFactory):
    class Meta:
        model = OAuthToken

    user = factory.SubFactory('common.tests.factories.users.UserFactory')


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.LazyAttribute(lambda o: f'{o.first_name}_{o.last_name}')
    email = factory.LazyAttribute(
        lambda a: '{}.{}@example.com'.format(a.first_name, a.last_name).lower()
    )
    password = 'pass'

    oauth_tokens = factory.RelatedFactoryList(OAuthUserTokenFactory, factory_related_name='user')
    oauth_info = factory.RelatedFactory(OAuthUserInfoFactory, factory_related_name='user')
