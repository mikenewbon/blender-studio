import datetime as dt
from typing import Any, Type, Union, Callable, Dict

from django.db.models.expressions import F, Value, Case, When
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet
from taggit.models import Tag

from blog.models import Revision
from films.models import Film, Asset, AssetCategory
from search.queries import add_common_annotations
from training.models import Training, Section, TrainingStatus, TrainingDifficulty

SearchableTrainingModel = Union[Training, Section, Asset]


def get_searchable_training_queryset(
    model: Type[SearchableTrainingModel], **filter_params: Any
) -> 'QuerySet[SearchableTrainingModel]':
    if model == Training:
        queryset = Training.objects.filter(
            status=TrainingStatus.published, **filter_params
        ).annotate(
            # project=F('name'),
            model=Value('training', output_field=CharField()),
            search_id=Concat(Value('training_'), 'id', output_field=CharField()),
        )
    elif model == Section:
        queryset = Section.objects.filter(
            chapter__training__status=TrainingStatus.published, **filter_params
        ).annotate(
            project=F('chapter__training__name'),
            chapter_name=F('chapter__name'),
            description=F('text'),
            difficulty=F('chapter__training__difficulty'),
            model=Value('section', output_field=CharField()),
            search_id=Concat(Value('section_'), 'id', output_field=CharField()),
        )
    elif model == Asset:
        queryset = Asset.objects.filter(
            is_published=True,
            film__is_published=True,
            category=AssetCategory.production_lesson,
            **filter_params,
        ).annotate(
            project=F('film__title'),
            type=Value(AssetCategory.production_lesson, output_field=CharField()),
            difficulty=Value(TrainingDifficulty.intermediate, output_field=CharField()),
            model=Value('asset', output_field=CharField()),
            search_id=Concat(Value('asset_'), 'id', output_field=CharField()),
        )
    else:
        raise TypeError(
            f'Inappropriate model class. `model` has to be one of Training, '
            f'Section, Asset; got {type(model)} instead.'
        )

    queryset = queryset.annotate(
        model=Value(model, output_field=CharField()),
        search_id=Concat(Value(f'{model}_'), 'id', output_field=CharField()),
    )

    return queryset


def set_individual_training_fields(
    instance_dict: Dict[Any, Any], instance: SearchableTrainingModel
) -> Dict[Any, Any]:
    instance_dict['url'] = instance.url
    instance_dict['timestamp'] = instance.date_created.timestamp()
    instance_dict['tags'] = [tag.name for tag in instance.tags.all()]

    if isinstance(instance, Training):
        instance_dict['thumbnail_url'] = instance.picture_16_9.url
        instance_dict['additional_tags'] = [
            tag.name
            for tag in Tag.objects.filter(section__chapter__training__pk=instance.pk).distinct()
        ]
    elif isinstance(instance, Section):
        instance_dict['thumbnail_url'] = instance.chapter.training.picture_16_9.url
        instance_dict['additional_tags'] = [
            tag.name for tag in instance.chapter.training.tags.all()
        ]
    elif isinstance(instance, Asset):
        instance_dict['thumbnail_url'] = (
            instance.static_asset.preview.url if instance.static_asset.preview else ''
        )
    else:
        raise TypeError(
            f'Inappropriate `instance` class. It has to be an instance of '
            f'Training, Section, or Asset; got {type(instance)} instead.'
        )

    return instance_dict
