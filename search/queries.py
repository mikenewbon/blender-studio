from typing import Any, Type, Union, Callable, Dict

from django.db.models.expressions import F, Value, Case, When
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query import QuerySet

from blog.models import Revision
from films.models import Film, Asset
from training.models import Training, Section, TrainingStatus

SearchableModels = Union[Film, Asset, Training, Section, Revision]


def get_searchable_queryset(
    model: Type[SearchableModels], **filter_params: Any
) -> 'QuerySet[SearchableModels]':
    get_queryset: Callable[..., 'QuerySet[SearchableModels]']
    if model == Film:
        get_queryset = get_searchable_films
    elif model == Asset:
        get_queryset = get_searchable_assets
    elif model == Training:
        get_queryset = get_searchable_trainings
    elif model == Section:
        get_queryset = get_searchable_sections
    elif model == Revision:
        get_queryset = get_searchable_posts
    else:
        raise TypeError(
            f'Inappropriate model class. `model` has to be one of Film, Asset, Training, '
            f'Section, Revision; got {type(model)} instead.'
        )

    return add_common_annotations(get_queryset(**filter_params))


def add_common_annotations(queryset: 'QuerySet[SearchableModels]') -> 'QuerySet[SearchableModels]':
    model = queryset.model._meta.model_name
    if model == 'revision':
        # 'Revision' is the actual model for internal use, but the user searches for posts
        model = 'post'
    return queryset.annotate(
        model=Value(model, output_field=CharField()),
        search_id=Concat(Value(f'{model}_'), 'id', output_field=CharField()),
    )


def get_searchable_films(**filter_params: Any) -> 'QuerySet[Film]':
    """Filters and annotates films queryset for the search index.

    Args:
        **filter_params: any additional filter parameters to filter the queryset by.

    Returns:
        A filtered and annotated Film queryset.
    """
    return Film.objects.filter(is_published=True, **filter_params).annotate(
        project=F('title'), name=F('title'),
    )


def get_searchable_assets(**filter_params: Any) -> 'QuerySet[Asset]':
    return Asset.objects.filter(
        is_published=True, film__is_published=True, **filter_params
    ).annotate(
        project=F('film__title'),
        collection_name=F('collection__name'),
        license=F('static_asset__license__name'),
        media_type=F('static_asset__source_type'),
    )


def get_searchable_trainings(**filter_params: Any) -> 'QuerySet[Training]':
    return Training.objects.filter(status=TrainingStatus.published, **filter_params).annotate(
        project=F('name'),
    )


def get_searchable_sections(**filter_params: Any) -> 'QuerySet[Section]':
    return Section.objects.filter(
        chapter__training__status=TrainingStatus.published, **filter_params
    ).annotate(
        project=F('chapter__training__name'),
        chapter_name=F('chapter__name'),
        description=F('text'),
    )


def get_searchable_posts(**filter_params: Any) -> 'QuerySet[Revision]':
    return (
        Revision.objects.filter(is_published=True, post__is_published=True, **filter_params)
        .order_by('post_id', '-date_created')
        .distinct('post_id')
        .annotate(
            project=Case(
                When(post__film__isnull=False, then=F('post__film__title')),
                default=Value(''),
                output_field=CharField(),
            ),
            name=F('title'),
        )
    )


def set_thumbnail_and_url(
    instance_dict: Dict[Any, Any], instance: SearchableModels
) -> Dict[Any, Any]:
    if isinstance(instance, Film):
        instance_dict['thumbnail_url'] = (
            instance.picture_16_9.url if instance.picture_16_9 else instance.picture_header.url
        )
    elif isinstance(instance, Asset):
        instance_dict['thumbnail_url'] = (
            instance.static_asset.preview.url if instance.static_asset.preview else ''
        )
    elif isinstance(instance, Training):
        instance_dict['thumbnail_url'] = instance.picture_16_9.url
    elif isinstance(instance, Section):
        instance_dict['thumbnail_url'] = instance.chapter.training.picture_16_9.url
    elif isinstance(instance, Revision):
        instance_dict['thumbnail_url'] = instance.picture_16_9.url
    else:
        raise TypeError(
            f'Inappropriate `instance` class. It has to be an instance of Film, Asset, '
            f'Training, Section, or Revision; got {type(instance)} instead.'
        )

    instance_dict['url'] = instance.url
    instance_dict['date_created_ts'] = (
        instance.post.date_created.timestamp()
        if isinstance(instance, Revision)
        else instance.date_created.timestamp()
    )

    return instance_dict
