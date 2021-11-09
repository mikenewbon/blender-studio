from abc import ABC
from html.parser import HTMLParser
from html import unescape
from io import StringIO
from typing import Optional, Any, Type, Dict, Union, Callable, List, TYPE_CHECKING
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.expressions import Value
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet

if TYPE_CHECKING:
    # ValuesQuerySet has long been removed from Django, but it is required by mypy
    from django.db.models.query import ValuesQuerySet

from blog.models import Post
from films.models import Film, Asset
from training.models import Training, Section

SearchableModel = Union[Film, Asset, Training, Section, Post]


class HTMLText(HTMLParser):
    def __init__(self):
        """Initialise HTML parser."""
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


class BaseSearchSerializer(ABC):
    """A base class for serializers of database data for indexing.

    Each concrete serializer class defines which objects will be added to a given index,
    and how they will be serialized.

    Attributes:
        models_to_index: A list of models to be added to the index.

        The following attributes are dicts whose keys are models, and values - dicts:
        filter_params: For each model, a dict with filter parameters for the queryset;
            filtering leaves the objects that should be available in search (e.g. published).
        annotations: For each model, a dict with model-specific annotations to be added to
            the queryset.
        additional_fields: For each model, a dict with additional fields to be added
            to each instance; the values of the fields are lambda functions, taking the
            instance as their only argument and returning the additional field's value.
    """

    models_to_index: List[Type[SearchableModel]]
    filter_params: Dict[Type[SearchableModel], Dict[str, Any]]
    annotations: Dict[Type[SearchableModel], Dict[str, Any]]
    additional_fields: Dict[Type[SearchableModel], Dict[str, Callable[[Any], Any]]]

    def get_searchable_queryset(
        self, model: Type[SearchableModel], **filter_params: Any
    ) -> 'QuerySet[SearchableModel]':
        """Only returns the model's objects that should be available in search."""
        filters = self.filter_params.get(model, {})
        filters.update(**filter_params)
        return model.objects.filter(**filters)

    def prepare_data_for_indexing(
        self, queryset: 'QuerySet[SearchableModel]'
    ) -> List[Dict[str, Any]]:
        """Serializes objects for search, adding all the necessary additional fields."""
        model = queryset.model

        queryset = self._add_common_annotations(queryset)
        queryset = queryset.annotate(**self.annotations.get(model, {}))
        qs_values = queryset.values()
        for instance_dict, instance in zip(qs_values, queryset):
            instance_dict = self._set_common_additional_fields(instance_dict, instance)
            for key, func in self.additional_fields.get(model, {}).items():
                instance_dict[key] = func(instance)

        return self._serialize_data(qs_values)

    def _add_common_annotations(
        self, queryset: 'QuerySet[SearchableModel]'
    ) -> 'QuerySet[SearchableModel]':
        """Adds queryset annotations common to all indexed objects: model and search_id."""
        model = queryset.model._meta.model_name

        return queryset.annotate(
            model=Value(model, output_field=CharField()),
            search_id=Concat(Value(f'{model}_'), 'id', output_field=CharField()),
        )

    def _set_common_additional_fields(
        self, instance_dict: Dict[Any, Any], instance: SearchableModel
    ) -> Dict[Any, Any]:
        """Adds fields common to all searchable models to the values dict of the instance."""
        instance_dict['url'] = instance.url
        instance_dict['timestamp'] = instance.date_created.timestamp()

        if hasattr(instance, 'description'):
            instance_dict['description'] = self.clean_html(instance.description)

        if isinstance(instance, Asset):
            instance_dict['thumbnail_url'] = (
                '' if not instance.static_asset else instance.static_asset.thumbnail_s_url
            )
        elif isinstance(instance, Section):
            instance_dict['thumbnail_url'] = instance.chapter.training.thumbnail_s_url or ''
        else:
            instance_dict['thumbnail_url'] = instance.thumbnail_s_url or ''
        return instance_dict

    def _serialize_data(
        self, qs_values: 'ValuesQuerySet[SearchableModel, Any]'
    ) -> List[Dict[str, Any]]:
        """Turns values queryset into a list of objects that can be added to a search index.

        The Index.add_documents method expects a list of objects, not a single object.
        Datetime values have to be serialized with DjangoJSONEncoder.
        """
        serialized_data: List[Dict[str, Any]] = json.loads(
            json.dumps(list(qs_values), cls=DjangoJSONEncoder)
        )
        return serialized_data

    @classmethod
    def clean_html(cls, text: Optional[str]) -> Optional[str]:
        """Strip HTML tags from given text."""
        if not text:
            return text
        s = HTMLText()
        s.feed(unescape(text))
        return s.get_data()

    @classmethod
    def clean_tag(cls, tag: Optional[str]) -> Optional[str]:
        """Replace '_' and '-' characters with spaces in a given tag."""
        if not tag:
            return tag
        return tag.replace('-', ' ').replace('_', ' ')
