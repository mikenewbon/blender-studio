import factory
from factory import fuzzy

from assets.models import StaticAsset, AssetFileTypeChoices, StorageLocation, License
from common.factories.user import UserFactory


class StorageBackendFactory(factory.DjangoModelFactory):
    class Meta:
        model = StorageLocation

    name = factory.Faker('text', max_nb_chars=15)


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

    source = factory.Faker('file_path')
    source_type = fuzzy.FuzzyChoice(AssetFileTypeChoices, getter=lambda c: c.value)
    size_bytes = 100
    user = factory.SubFactory(UserFactory)
    license = factory.SubFactory(LicenseFactory)
    storage_backend = factory.SubFactory(StorageBackendFactory)
