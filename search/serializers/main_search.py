import datetime as dt
from typing import Any, Type, Dict

from django.db.models.expressions import F, Value, Case, When
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q

from blog.models import Revision
from films.models import Film, Asset
from search.serializers.base import SearchableModel, SearchModelSetup, BaseSearchSerializer
from search.serializers.training_search import TRAINING_SEARCH_SETUP
from training.models import Training, Section

SEARCH_SETUP: Dict[Type[SearchableModel], SearchModelSetup] = {
    Film: {
        'filter_params': {'is_published': True},
        'annotations': {'project': F('title'), 'name': F('title')},
        'additional_fields': {
            'thumbnail_url': (
                lambda instance: instance.picture_16_9.url
                if instance.picture_16_9
                else instance.picture_header.url
            ),
            'timestamp': (
                lambda instance: dt.datetime(
                    year=instance.release_date.year,
                    month=instance.release_date.month,
                    day=instance.release_date.day,
                ).timestamp()
                if instance.release_date
                else instance.date_created.timestamp()
            ),
        },
    },
    Asset: {
        'filter_params': {'is_published': True, 'film__is_published': True},
        'annotations': {
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
        'additional_fields': TRAINING_SEARCH_SETUP[Asset]['additional_fields'],
    },
    Training: {
        'filter_params': TRAINING_SEARCH_SETUP[Training]['filter_params'],
        'annotations': {'project': F('name')},
        'additional_fields': TRAINING_SEARCH_SETUP[Training]['additional_fields'],
    },
    Section: {
        'filter_params': TRAINING_SEARCH_SETUP[Section]['filter_params'],
        'annotations': {
            'project': F('chapter__training__name'),
            'chapter_name': F('chapter__name'),
            'description': F('text'),
            'media_type': Case(
                When(Q(video__isnull=False, assets__isnull=False), then=Value('video file')),
                When(video__isnull=False, then=Value('video')),
                When(assets__isnull=False, then=Value('file')),
                output_field=CharField(),
            ),
            # Attributes for faceting have to be string type, not boolean:
            'free': Case(
                When(is_free=True, then=Value('true')),
                default=Value('false'),
                output_field=CharField(),
            ),
        },
        'additional_fields': {
            'thumbnail_url': lambda instance: instance.chapter.training.picture_16_9.url,
            'timestamp': lambda instance: instance.date_created.timestamp(),
            'tags': lambda instance: [tag.name for tag in instance.tags.all()],
            'additional_tags': (
                lambda instance: [tag.name for tag in instance.chapter.training.tags.all()]
            ),
            'media_type': (
                lambda instance: instance.media_type.split() if instance.media_type else []
            ),
        },
    },
    Revision: {
        'filter_params': {'is_published': True, 'post__is_published': True},
        'annotations': {
            'project': Case(
                When(post__film__isnull=False, then=F('post__film__title')),
                default=Value(''),
                output_field=CharField(),
            ),
            'name': F('title'),
        },
        'additional_fields': {
            'thumbnail_url': lambda instance: instance.picture_16_9.url,
            'timestamp': lambda instance: instance.post.date_created.timestamp(),
        },
    },
}


class MainSearchSerializer(BaseSearchSerializer):
    """Prepare database objects to be indexed"""

    models_to_index = [Film, Asset, Training, Section, Revision]
    setup = SEARCH_SETUP

    def get_searchable_queryset(
        self, model: Type[SearchableModel], **filter_params: Any
    ) -> 'QuerySet[SearchableModel]':
        queryset = super().get_searchable_queryset(model, **filter_params)

        if model == Revision:
            queryset = queryset.order_by('post_id', '-date_created').distinct('post_id')

        return queryset

    def add_common_annotations(
        self, queryset: 'QuerySet[SearchableModel]',
    ) -> 'QuerySet[SearchableModel]':
        model = queryset.model._meta.model_name
        if model == 'revision':
            # 'Revision' is the actual model for internal use, but the user searches for posts.
            # Also: the search_id is set to post's id so that a new revision always overwrites
            # the previous one, which should not be searchable any more.
            return queryset.annotate(
                model=Value('post', output_field=CharField()),
                search_id=Concat(Value('post_'), 'post__id', output_field=CharField()),
            )
        return super().add_common_annotations(queryset)
