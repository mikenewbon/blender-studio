import datetime as dt
from typing import Any, Type, Dict

from django.db.models.expressions import F, Value, Case, When
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet
from taggit.models import Tag

from blog.models import Revision
from films.models import Film, Asset
from search.serializers.base import SearchableModel, BaseSearchSerializer
from training.models import Training, Section, TrainingStatus


class MainSearchSerializer(BaseSearchSerializer):
    """Prepare database objects to be indexed in the main search index."""

    models_to_index = [Film, Asset, Training, Section, Revision]
    filter_params = {
        Film: {'is_published': True},
        Asset: {'is_published': True, 'film__is_published': True},
        Training: {'status': TrainingStatus.published},
        Section: {'chapter__training__status': TrainingStatus.published},
        Revision: {'is_published': True, 'post__is_published': True},
    }
    annotations = {
        Film: {'project': F('title'), 'name': F('title')},
        Asset: {
            'project': F('film__title'),
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
        Training: {'project': F('name')},
        Section: {
            'project': F('chapter__training__name'),
            'chapter_name': F('chapter__name'),
            'description': F('text'),
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
        Revision: {
            'project': Case(
                When(post__film__isnull=False, then=F('post__film__title')),
                default=Value(''),
                output_field=CharField(),
            ),
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
            'secondary_tags': (
                lambda instance: [tag.name for tag in instance.chapter.training.tags.all()]
            ),
            'media_type': (
                lambda instance: instance.media_type.split() if instance.media_type else []
            ),
        },
        Revision: {},
    }

    def get_searchable_queryset(
        self, model: Type[SearchableModel], **filter_params: Any
    ) -> 'QuerySet[SearchableModel]':
        queryset = super().get_searchable_queryset(model, **filter_params)

        if model == Revision:
            # Only the latest revision of a post should be available in search
            queryset = queryset.order_by('post_id', '-date_created').distinct('post_id')

        return queryset

    def _add_common_annotations(
        self, queryset: 'QuerySet[SearchableModel]',
    ) -> 'QuerySet[SearchableModel]':
        model = queryset.model._meta.model_name
        if model == 'revision':
            # 'Revision' is the actual model for internal use, but the user searches for posts.
            # Also: the search_id is set to post's id, so that in the search index a new revision
            # always overwrites the previous one, which should not be searchable any more.
            return queryset.annotate(
                model=Value('post', output_field=CharField()),
                search_id=Concat(Value('post_'), 'post__id', output_field=CharField()),
            )
        return super()._add_common_annotations(queryset)

    def _set_common_additional_fields(
        self, instance_dict: Dict[Any, Any], instance: SearchableModel
    ) -> Dict[Any, Any]:
        instance_dict = super()._set_common_additional_fields(instance_dict, instance)

        if isinstance(instance, Revision):
            instance_dict['timestamp'] = instance.post.date_created.timestamp()
        elif isinstance(instance, Film) and instance.release_date is not None:
            instance_dict['timestamp'] = dt.datetime(
                year=instance.release_date.year,
                month=instance.release_date.month,
                day=instance.release_date.day,
            ).timestamp()

        return instance_dict
