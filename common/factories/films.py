import factory

from common.factories.assets import StaticAssetFactory, StorageBackendFactory
from common.factories.user import UserFactory
from films.models import (
    Film,
    Collection,
    Asset,
    ProductionLog,
    ProductionLogEntry,
    ProductionLogEntryAsset,
)


class FilmFactory(factory.DjangoModelFactory):
    class Meta:
        model = Film

    title = factory.Faker('text', max_nb_chars=20)
    slug = factory.Faker('slug')
    is_published = True

    storage_backend = factory.SubFactory(StorageBackendFactory)


class CollectionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Collection

    film = factory.SubFactory(FilmFactory)
    name = factory.Faker('text', max_nb_chars=30)
    slug = factory.Faker('slug')

    storage_backend = factory.SelfAttribute('film.storage_backend')


class AssetFactory(factory.DjangoModelFactory):
    class Meta:
        model = Asset

    film = factory.SubFactory(FilmFactory)
    collection = factory.SubFactory(CollectionFactory, film=factory.SelfAttribute('..film'))
    static_asset = factory.SubFactory(
        StaticAssetFactory, storage_backend=factory.SelfAttribute('..film.storage_backend')
    )

    name = factory.Faker('text', max_nb_chars=30)
    is_published = True


class ProductionLogFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProductionLog

    film = factory.SubFactory(FilmFactory)
    summary = factory.Faker('text')
    user = factory.SubFactory(UserFactory)
    storage_backend = factory.SelfAttribute('film.storage_backend')
    picture_16_9 = factory.Faker('file_path', category='image')


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
