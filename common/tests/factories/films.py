import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from common.tests.factories.helpers import generate_image_path
from common.tests.factories.static_assets import StaticAssetFactory
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
    FilmFlatPage,
)
from search import signals as search_signals


@factory.django.mute_signals(search_signals.post_save)
class FilmFactory(DjangoModelFactory):
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
    thumbnail = factory.LazyFunction(generate_image_path)


@factory.django.mute_signals(search_signals.post_save)
class CollectionFactory(DjangoModelFactory):
    class Meta:
        model = Collection

    film = factory.SubFactory(FilmFactory)
    name = factory.Faker('text', max_nb_chars=30)
    slug = factory.Faker('slug')
    text = factory.Faker('paragraph')

    thumbnail = factory.LazyFunction(generate_image_path)


@factory.django.mute_signals(search_signals.post_save)
class AssetFactory(DjangoModelFactory):
    class Meta:
        model = Asset

    film = factory.SubFactory(FilmFactory)
    collection = factory.SubFactory(CollectionFactory, film=factory.SelfAttribute('..film'))
    static_asset = factory.SubFactory(StaticAssetFactory)

    name = factory.Faker('text', max_nb_chars=30)
    slug = factory.Faker('slug')
    description = factory.Faker('paragraph')
    category = fuzzy.FuzzyChoice(AssetCategory.choices, getter=lambda c: c[0])
    is_published = True


@factory.django.mute_signals(search_signals.post_save)
class ProductionLogFactory(DjangoModelFactory):
    class Meta:
        model = ProductionLog

    film = factory.SubFactory(FilmFactory)
    summary = factory.Faker('text')
    user = factory.SubFactory(UserFactory)
    thumbnail = factory.LazyFunction(generate_image_path)


class ProductionLogEntryFactory(DjangoModelFactory):
    class Meta:
        model = ProductionLogEntry

    production_log = factory.SubFactory(ProductionLogFactory)
    description = factory.Faker('text')
    user = factory.SubFactory(UserFactory)


class ProductionLogEntryAssetFactory(DjangoModelFactory):
    class Meta:
        model = ProductionLogEntryAsset

    asset = factory.SubFactory(AssetFactory)
    production_log_entry = factory.SubFactory(ProductionLogEntryFactory)


class FilmFlatPageFactory(DjangoModelFactory):
    class Meta:
        model = FilmFlatPage

    film = factory.SubFactory(FilmFactory)
    title = factory.Faker('word')
    content = factory.Faker('text')
