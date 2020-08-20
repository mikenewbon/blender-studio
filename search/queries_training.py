from typing import Any, Type, Union, Callable, Dict

from django.db.models.expressions import F, Value
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet
from taggit.models import Tag

from films.models import Asset, AssetCategory
from training.models import Training, Section, TrainingStatus

SearchableTrainingModel = Union[Training, Section, Asset]


def get_searchable_queryset_for_training(
    model: Type[SearchableTrainingModel], **filter_params: Any
) -> 'QuerySet[SearchableTrainingModel]':
    get_queryset: Callable[..., 'QuerySet[SearchableTrainingModel]']
    if model == Training:
        get_queryset = get_searchable_trainings_for_training
    elif model == Section:
        get_queryset = get_searchable_sections_for_training
    elif model == Asset:
        get_queryset = get_searchable_assets_for_training
    else:
        raise TypeError(
            f'Inappropriate model class. `model` has to be one of Training, '
            f'Section, Asset; got {type(model)} instead.'
        )

    return get_queryset(**filter_params).annotate(
        model=Value(model, output_field=CharField()),
        search_id=Concat(Value(f'{model}_'), 'id', output_field=CharField()),
    )


def get_searchable_trainings_for_training(**filter_params: Any) -> 'QuerySet[Training]':
    return Training.objects.filter(status=TrainingStatus.published, **filter_params)


def get_searchable_sections_for_training(**filter_params: Any) -> 'QuerySet[Section]':
    return Section.objects.filter(
        chapter__training__status=TrainingStatus.published, **filter_params
    ).annotate(
        project=F('chapter__training__name'),
        chapter_name=F('chapter__name'),
        description=F('text'),
    )


def get_searchable_assets_for_training(**filter_params: Any) -> 'QuerySet[Asset]':
    return Asset.objects.filter(
        is_published=True,
        film__is_published=True,
        category=AssetCategory.production_lesson,
        **filter_params,
    ).annotate(
        project=F('film__title'),
        type=Value(AssetCategory.production_lesson, output_field=CharField()),
    )


def set_individual_fields_for_training(
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
