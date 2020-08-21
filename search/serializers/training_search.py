from typing import Type, Dict

from django.db.models.expressions import F, Value
from django.db.models.fields import CharField
from taggit.models import Tag

from films.models import Asset, AssetCategory
from search.serializers.base import SearchableModel, SearchModelSetup, BaseSearchSerializer
from training.models import Training, Section, TrainingStatus

TRAINING_SEARCH_SETUP: Dict[Type[SearchableModel], SearchModelSetup] = {
    Training: {
        'filter_params': {'status': TrainingStatus.published},
        'annotations': {},
        'additional_fields': {
            'thumbnail_url': lambda instance: instance.picture_16_9.url,
            'timestamp': lambda instance: instance.date_created.timestamp(),
            'tags': lambda instance: [tag.name for tag in instance.tags.all()],
            'additional_tags': lambda instance: [
                tag.name
                for tag in Tag.objects.filter(section__chapter__training__pk=instance.pk).distinct()
            ],
        },
    },
    Section: {
        'filter_params': {'chapter__training__status': TrainingStatus.published},
        'annotations': {
            'project': F('chapter__training__name'),
            'chapter_name': F('chapter__name'),
            'description': F('text'),
        },
        'additional_fields': {
            'thumbnail_url': lambda instance: instance.chapter.training.picture_16_9.url,
            'timestamp': lambda instance: instance.date_created.timestamp(),
            'tags': lambda instance: [tag.name for tag in instance.tags.all()],
            'additional_tags': (
                lambda instance: [tag.name for tag in instance.chapter.training.tags.all()]
            ),
        },
    },
    Asset: {
        'filter_params': {
            'is_published': True,
            'film__is_published': True,
            'category': AssetCategory.production_lesson,
        },
        'annotations': {
            'project': F('film__title'),
            'type': Value(AssetCategory.production_lesson, output_field=CharField()),
        },
        'additional_fields': {
            'thumbnail_url': (
                lambda instance: instance.static_asset.preview.url
                if instance.static_asset.preview
                else ''
            ),
            'timestamp': lambda instance: instance.date_created.timestamp(),
            'tags': lambda instance: [tag.name for tag in instance.tags.all()],
        },
    },
}


class TrainingSearchSerializer(BaseSearchSerializer):
    models_to_index = [Training, Section, Asset]
    setup = TRAINING_SEARCH_SETUP
