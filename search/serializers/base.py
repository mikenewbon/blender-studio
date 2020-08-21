import json
from abc import ABC
from typing import Union, TypedDict, Dict, Any, Callable, List, Type, TYPE_CHECKING

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.expressions import Value
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet

if TYPE_CHECKING:
    from django.db.models.query import ValuesQuerySet

from blog.models import Revision
from films.models import Film, Asset
from training.models import Training, Section

SearchableModel = Union[Film, Asset, Training, Section, Revision]


class SearchModelSetup(TypedDict):
    filter_params: Dict[str, Any]
    annotations: Dict[str, Any]
    additional_fields: Dict[str, Callable[[Any], Any]]


class BaseSearchSerializer(ABC):
    models_to_index: List[Type[SearchableModel]]
    setup: Dict[Type[SearchableModel], SearchModelSetup]

    def get_searchable_queryset(
        self, model: Type[SearchableModel], **filter_params: Any
    ) -> 'QuerySet[SearchableModel]':
        filters = self.setup[model]['filter_params']
        filters.update(**filter_params)
        return model.objects.filter(**filters)

    def prepare_data_for_indexing(
        self, queryset: 'QuerySet[SearchableModel]',
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
        self, queryset: 'QuerySet[SearchableModel]',
    ) -> 'QuerySet[SearchableModel]':
        model = queryset.model._meta.model_name

        return queryset.annotate(
            model=Value(model, output_field=CharField()),
            search_id=Concat(Value(f'{model}_'), 'id', output_field=CharField()),
        )

    @staticmethod
    def set_common_additional_fields(
        instance_dict: Dict[Any, Any], instance: SearchableModel
    ) -> Dict[Any, Any]:
        instance_dict['url'] = instance.url

        return instance_dict

    @staticmethod
    def serialize_data(qs_values: 'ValuesQuerySet[SearchableModel, Any]') -> List[Dict[str, Any]]:
        """Turns values queryset into a list of objects that can be added to a search index.

        The Index.add_documents method expects a list of objects, not a single object.
        Datetime values have to be serialized with DjangoJSONEncoder.
        """
        serialized_data: List[Dict[str, Any]] = json.loads(
            json.dumps(list(qs_values), cls=DjangoJSONEncoder)
        )
        return serialized_data
