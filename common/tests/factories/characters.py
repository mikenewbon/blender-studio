from factory.django import DjangoModelFactory
import factory

from characters.models import Character, CharacterVersion, CharacterShowcase
from common.tests.factories.static_assets import StaticAssetFactory


class CharacterFactory(DjangoModelFactory):
    class Meta:
        model = Character

    name = factory.Faker('text', max_nb_chars=20)
    slug = factory.Faker('slug')


class CharacterVersionFactory(DjangoModelFactory):
    class Meta:
        model = CharacterVersion

    character = factory.SubFactory(CharacterFactory)
    static_asset = factory.SubFactory(StaticAssetFactory)
    preview_video_static_asset = factory.SubFactory(StaticAssetFactory)
    number = 1
    description = factory.Faker('sentence')


class CharacterShowcaseFactory(DjangoModelFactory):
    class Meta:
        model = CharacterShowcase

    character = factory.SubFactory(CharacterFactory)
    static_asset = factory.SubFactory(StaticAssetFactory)
    preview_video_static_asset = factory.SubFactory(StaticAssetFactory)
    description = factory.Faker('sentence')
    title = factory.Faker('text', max_nb_chars=20)
