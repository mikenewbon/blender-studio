import json
from typing import Any, Type, Union, Dict, List, TypedDict, Callable

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import Model
from django.db.models.expressions import F, Value
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet
from taggit.models import Tag

from common.types import assert_cast
from films.models import Asset, AssetCategory
from training.models import Training, Section, TrainingStatus

SearchableTrainingModel = Union[Training, Section, Asset]


class SearchModelSetup(TypedDict):
    filter_params: Dict[str, Any]
    annotations: Dict[str, Any]
    additional_fields: Dict[str, Callable[[Any], Any]]


TRAINING_SEARCH_SETUP: Dict[Type[SearchableTrainingModel], SearchModelSetup] = {
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


class BaseSearchParser:
    models_to_index: List[Type[Model]] = [Training, Section, Asset]
    setup: Dict[Type[SearchableTrainingModel], SearchModelSetup] = TRAINING_SEARCH_SETUP

    def get_searchable_queryset(
        self, model: Type[SearchableTrainingModel], **filter_params: Any
    ) -> 'QuerySet[SearchableTrainingModel]':
        filters = self.setup[model]['filter_params']
        filters.update(**filter_params)
        return model.objects.filter(**filters)

    def prepare_data_for_indexing(
        self, queryset: 'QuerySet[SearchableTrainingModel]',
    ) -> List[Dict[str, Any]]:
        model = queryset.model
        annotations = self.setup[model]['annotations']
        additional_fields = self.setup[model]['additional_fields']

        queryset = self.add_common_annotations(queryset)
        queryset = queryset.annotate(**annotations)
        qs_values = queryset.values()
        for instance_dict, instance in zip(qs_values, queryset):
            instance_dict = self.set_common_additional_fields(instance_dict, instance)
            for key, func in additional_fields.items():
                instance_dict[key] = func(instance)
        # TODO: do we need datetime fields? Don't add them and get rid of JSON encoder?
        return self.serialize_data(qs_values)

    def add_common_annotations(
        self, queryset: 'QuerySet[SearchableTrainingModel]',
    ) -> 'QuerySet[SearchableTrainingModel]':
        model = queryset.model._meta.model_name

        return queryset.annotate(
            model=Value(model, output_field=CharField()),
            search_id=Concat(Value(f'{model}_'), 'id', output_field=CharField()),
        )

    @staticmethod
    def set_common_additional_fields(
        instance_dict: Dict[Any, Any], instance: SearchableTrainingModel
    ) -> Dict[Any, Any]:
        instance_dict['url'] = instance.url

        return instance_dict

    @staticmethod
    def serialize_data(qs_values: 'QuerySet[SearchableTrainingModel]') -> List[Dict[str, Any]]:
        """Turns values queryset into a list of objects that can be added to a search index.

        The Index.add_documents method expects a list of objects, not a single object.
        Datetime values have to be serialized with DjangoJSONEncoder.
        """
        data_to_load = list(qs_values)
        return assert_cast(
            List[Dict[str, Any]], json.loads(json.dumps(data_to_load, cls=DjangoJSONEncoder))
        )


class TrainingSearchParser(BaseSearchParser):
    pass
