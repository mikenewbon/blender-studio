import uuid

import factory
from factory import fuzzy

from common.tests.factories.static_assets import StaticAssetFactory, StorageLocationFactory
from common.tests.factories.users import UserFactory
from films.models import (
    Film,
    Collection,
    Asset,
    ProductionLog,
    ProductionLogEntry,
    ProductionLogEntryAsset,
    FilmStatus,
    AssetCategory,
)


def generate_image_path() -> str:
    return f'tests/images/{uuid.uuid4()}.jpg'


class FilmFactory(factory.DjangoModelFactory):
    class Meta:
        model = Film

    title = factory.Faker('text', max_nb_chars=20)
    slug = factory.Faker('slug')
    description = factory.Faker('sentence')
    summary = factory.Faker('paragraph')
    status = fuzzy.FuzzyChoice(FilmStatus.choices, getter=lambda c: c[0])
    release_date = factory.Faker('date')
    is_published = True

    logo = factory.LazyFunction(generate_image_path)
    poster = factory.LazyFunction(generate_image_path)
    picture_header = factory.LazyFunction(generate_image_path)

    storage_location = factory.SubFactory(
        StorageLocationFactory, name=factory.SelfAttribute('..title')
    )


class CollectionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Collection

    film = factory.SubFactory(FilmFactory)
    name = factory.Faker('text', max_nb_chars=30)
    slug = factory.Faker('slug')
    text = factory.Faker('paragraph')

    storage_location = factory.SelfAttribute('film.storage_location')


class AssetFactory(factory.DjangoModelFactory):
    class Meta:
        model = Asset

    film = factory.SubFactory(FilmFactory)
    collection = factory.SubFactory(CollectionFactory, film=factory.SelfAttribute('..film'))
    static_asset = factory.SubFactory(
        StaticAssetFactory, storage_location=factory.SelfAttribute('..film.storage_location')
    )

    name = factory.Faker('text', max_nb_chars=30)
    slug = factory.Faker('slug')
    description = factory.Faker('paragraph')
    category = fuzzy.FuzzyChoice(AssetCategory.choices, getter=lambda c: c[0])
    is_published = True


class ProductionLogFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProductionLog

    film = factory.SubFactory(FilmFactory)
    summary = factory.Faker('text')
    user = factory.SubFactory(UserFactory)
    storage_location = factory.SelfAttribute('film.storage_location')
    picture_16_9 = factory.LazyFunction(generate_image_path)


class ProductionLogEntryFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProductionLogEntry

    production_log = factory.SubFactory(ProductionLogFactory)
    description = factory.Faker('text')
    user = factory.SubFactory(UserFactory)
    author_role = factory.Faker('job')


class ProductionLogEntryAssetFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProductionLogEntryAsset

    asset = factory.SubFactory(AssetFactory)
    production_log_entry = factory.SubFactory(ProductionLogEntryFactory)
