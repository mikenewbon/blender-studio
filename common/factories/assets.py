import random
import uuid

import factory
from django.conf import settings
from factory import fuzzy

from assets.models import StaticAsset, AssetFileTypeChoices, StorageLocation, License
from common.factories.user import UserFactory


def generate_file_path() -> str:
    extensions = ['jpg', 'png', 'blend', 'mp4', 'mov']
    return f'tests/assets/{uuid.uuid4()}.{random.choice(extensions)}'


class StorageLocationFactory(factory.DjangoModelFactory):
    class Meta:
        model = StorageLocation
        django_get_or_create = ('name',)

    name = factory.Faker('text', max_nb_chars=30)


class LicenseFactory(factory.DjangoModelFactory):
    class Meta:
        model = License

    name = factory.Faker('text', max_nb_chars=15)
    slug = factory.Faker('slug')
    description = factory.Faker('text')
    url = factory.Faker('url')


class StaticAssetFactory(factory.DjangoModelFactory):
    class Meta:
        model = StaticAsset

    source = factory.LazyFunction(generate_file_path)
    source_type = fuzzy.FuzzyChoice(AssetFileTypeChoices, getter=lambda c: c.value)
    size_bytes = 100
    user = factory.SubFactory(UserFactory)
    license = factory.SubFactory(LicenseFactory)
    storage_location = factory.SubFactory(StorageLocationFactory)
