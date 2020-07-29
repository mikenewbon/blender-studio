import factory
from factory import fuzzy

from common.tests.factories.films import generate_image_path
from common.tests.factories.static_assets import StorageLocationFactory
from training.models import Training, TrainingStatus, TrainingType, TrainingDifficulty


class TrainingFactory(factory.DjangoModelFactory):
    class Meta:
        model = Training

    name = factory.Faker('text', max_nb_chars=20)
    slug = factory.Faker('slug')
    description = factory.Faker('sentence')
    summary = factory.Faker('paragraph')
    status = fuzzy.FuzzyChoice(TrainingStatus.choices, getter=lambda c: c[0])
    type = fuzzy.FuzzyChoice(TrainingType.choices, getter=lambda c: c[0])
    difficulty = fuzzy.FuzzyChoice(TrainingDifficulty.choices, getter=lambda c: c[0])
    picture_header = factory.LazyFunction(generate_image_path)
    picture_16_9 = factory.LazyFunction(generate_image_path)
    storage_location = factory.SubFactory(
        StorageLocationFactory, name=factory.SelfAttribute('..name')
    )
