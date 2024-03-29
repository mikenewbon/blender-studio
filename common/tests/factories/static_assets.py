import datetime
import factory
import random
from factory import fuzzy
from factory.django import DjangoModelFactory

from common.tests.factories.helpers import generate_file_path
from common.tests.factories.users import UserFactory
from static_assets.models import (
    License,
    StaticAsset,
    StaticAssetFileTypeChoices,
    Video,
    VideoVariation,
)


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

    id = factory.Sequence(lambda n: n)
    # TODO: Generate realistic names, based on file type
    original_filename = "original_name"
    source = factory.LazyFunction(generate_file_path)
    source_type = fuzzy.FuzzyChoice(StaticAssetFileTypeChoices, getter=lambda c: c.value)
    size_bytes = 100
    user = factory.SubFactory(UserFactory)
    license = factory.SubFactory(LicenseFactory)
    thumbnail = factory.LazyFunction(generate_file_path)


class VideoFactory(DjangoModelFactory):
    class Meta:
        model = Video

    static_asset = factory.SubFactory(StaticAssetFactory)
    duration = datetime.timedelta(seconds=0)


class VideoVariationFactory(DjangoModelFactory):
    class Meta:
        model = VideoVariation

    size_bytes = factory.LazyFunction(lambda: random.randint(0, 100 ** 3))
    resolution_label = '720p'
    source = factory.LazyFunction(generate_file_path)
    video = factory.SubFactory(VideoFactory)
