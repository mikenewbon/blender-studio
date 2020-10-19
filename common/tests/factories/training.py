import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from common.tests.factories.helpers import generate_image_path
from search import signals as search_signals
from training.models import (
    Training,
    TrainingStatus,
    TrainingType,
    TrainingDifficulty,
    Chapter,
    Section,
)


@factory.django.mute_signals(search_signals.post_save)
class TrainingFactory(DjangoModelFactory):
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
    thumbnail = factory.LazyFunction(generate_image_path)


class ChapterFactory(DjangoModelFactory):
    class Meta:
        model = Chapter

    training = factory.SubFactory(TrainingFactory)
    index = factory.Sequence(lambda n: n)
    name = factory.Faker('text', max_nb_chars=20)
    slug = factory.Faker('slug')


@factory.django.mute_signals(search_signals.post_save)
class SectionFactory(DjangoModelFactory):
    class Meta:
        model = Section

    chapter = factory.SubFactory(ChapterFactory)
    index = factory.Sequence(lambda n: n)
    name = factory.Faker('text', max_nb_chars=20)
    slug = factory.Faker('slug')
    text = factory.Faker('text')
