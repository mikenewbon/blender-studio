import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from common.tests.factories.helpers import generate_file_path
from common.tests.factories.users import UserFactory
from static_assets.models import StaticAsset, StaticAssetFileTypeChoices, StorageLocation, License


class StorageLocationFactory(DjangoModelFactory):
    class Meta:
        model = StorageLocation
        django_get_or_create = ('name',)

    name = factory.Faker('text', max_nb_chars=30)


class LicenseFactory(DjangoModelFactory):
    class Meta:
        model = License

    name = factory.Faker('text', max_nb_chars=15)
    slug = factory.Faker('slug')
    description = factory.Faker('text')
    url = factory.Faker('url')


class StaticAssetFactory(DjangoModelFactory):
    class Meta:
        model = StaticAsset

    source = factory.LazyFunction(generate_file_path)
    source_type = fuzzy.FuzzyChoice(StaticAssetFileTypeChoices, getter=lambda c: c.value)
    size_bytes = 100
    user = factory.SubFactory(UserFactory)
    license = factory.SubFactory(LicenseFactory)
    storage_location = factory.SubFactory(StorageLocationFactory)
