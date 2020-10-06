import factory
from django.contrib.auth.models import User
from factory.django import DjangoModelFactory

from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken


class OAuthUserInfoFactory(DjangoModelFactory):
    class Meta:
        model = OAuthUserInfo
    user = factory.SubFactory('common.tests.factories.users.UserFactory')


class OAuthUserTokenFactory(DjangoModelFactory):
    class Meta:
        model = OAuthToken
    user = factory.SubFactory('common.tests.factories.users.UserFactory')


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.LazyAttribute(lambda o: f'{o.first_name}_{o.last_name}')
    password = 'pass'

    oauth_tokens = factory.RelatedFactory(OAuthUserTokenFactory, factory_related_name='user')
    oauth_info = factory.RelatedFactory(OAuthUserInfoFactory, factory_related_name='user')
