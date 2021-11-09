from typing import Any, Type, Dict
import datetime as dt

from django.db.models.expressions import F, Value, Case, When
from django.db.models.fields import CharField
from django.db.models.query import QuerySet
from taggit.models import Tag

from blog.models import Post
from films.models import Film, Asset
from search.serializers.base import SearchableModel, BaseSearchSerializer
from training.models import Training, Section


class MainSearchSerializer(BaseSearchSerializer):
    """Prepare database objects to be indexed in the main search index."""

    models_to_index = [Film, Asset, Training, Section, Post]
    filter_params = {
        Film: {'is_published': True},
        Asset: {'is_published': True, 'film__is_published': True},
        Training: {'is_published': True},
        Section: {
            'chapter__is_published': True,
            'chapter__training__is_published': True,
            'is_published': True,
        },
        Post: {'is_published': True},
    }
    annotations = {
        Film: {'name': F('title')},
        Asset: {
            'author_name': Case(
                When(static_asset__author__isnull=False, then=F('static_asset__author__full_name')),
                default=F('static_asset__user__full_name'),
                output_field=CharField(),
            ),
            'film_title': F('film__title'),
            'collection_name': F('collection__name'),
            'license': F('static_asset__license__name'),
            'media_type': F('static_asset__source_type'),
            # Attributes for faceting have to be string type, not bool:
            'free': Case(
                When(is_free=True, then=Value('true')),
                default=Value('false'),
                output_field=CharField(),
            ),
        },
        Training: {},
        Section: {
            'author_name': F('user__full_name'),
            'training_name': F('chapter__training__name'),
            'chapter_name': F('chapter__name'),
            'media_type': Case(
                When(static_asset__isnull=False, then=F('static_asset__source_type')),
                output_field=CharField(),
            ),
            # Attributes for faceting have to be string type, not boolean:
            'free': Case(
                When(is_free=True, then=Value('true')),
                default=Value('false'),
                output_field=CharField(),
            ),
        },
        Post: {
            'author_name': F('author__full_name'),
            'film_title': F('film__title'),
            'name': F('title'),
        },
    }
    additional_fields = {
        Film: {},
        Asset: {'tags': lambda instance: [tag.name for tag in instance.tags.all()]},
        Training: {
            'tags': lambda instance: [tag.name for tag in instance.tags.all()],
            'secondary_tags': lambda instance: [
                tag.name
                for tag in Tag.objects.filter(section__chapter__training__pk=instance.pk).distinct()
            ],
        },
        Section: {
            'tags': lambda instance: [tag.name for tag in instance.tags.all()],
            'description': lambda instance: BaseSearchSerializer.clean_html(instance.text),
            'secondary_tags': (
                lambda instance: [tag.name for tag in instance.chapter.training.tags.all()]
            ),
            'media_type': (
                lambda instance: instance.media_type.split() if instance.media_type else []
            ),
        },
        Post: {'description': lambda instance: '' if not instance.excerpt else instance.excerpt},
    }

    def get_searchable_queryset(
        self, model: Type[SearchableModel], **filter_params: Any
    ) -> 'QuerySet[SearchableModel]':
        queryset = super().get_searchable_queryset(model, **filter_params)

        return queryset

    def _set_common_additional_fields(
        self, instance_dict: Dict[Any, Any], instance: SearchableModel
    ) -> Dict[Any, Any]:
        instance_dict = super()._set_common_additional_fields(instance_dict, instance)

        if isinstance(instance, Post):
            # TODO(fsiddi) Switch to date_published, and take care of 'None' case
            instance_dict['timestamp'] = instance.date_created.timestamp()
        elif isinstance(instance, Film) and instance.release_date is not None:
            instance_dict['timestamp'] = dt.datetime(
                year=instance.release_date.year,
                month=instance.release_date.month,
                day=instance.release_date.day,
            ).timestamp()

        return instance_dict
