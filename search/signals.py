import json
import logging
from typing import Union, Type, Any, Dict

import meilisearch
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.expressions import F, Value, Case, When
from django.db.models.fields import CharField
from django.db.models.signals import post_save
from django.dispatch import receiver

from blog.models import Revision
from films.models import Film, Asset
from search.management.commands.create_search_index import SEARCHABLE_ATTRIBUTES
from training.models import Training, Section, TrainingStatus

log = logging.getLogger(__name__)

SearchableModels = Union[Film, Asset, Training, Section, Revision]


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Revision)
def update_search_index(
    sender: Type[SearchableModels], instance: SearchableModels, **kwargs: Any
) -> None:
    instance_dict: Dict[str, Any] = {}
    if isinstance(instance, Film) and instance.is_published:
        instance_qs = sender.objects.filter(id=instance.id).annotate(
            project=F('title'), name=F('title'),
        )
        instance_dict = instance_qs.values().get()
        instance_dict['thumbnail_url'] = (
            instance.picture_16_9.url if instance.picture_16_9 else instance.picture_header.url
        )
    elif isinstance(instance, Asset) and instance.is_published and instance.film.is_published:
        instance_qs = sender.objects.filter(id=instance.id).annotate(
            project=F('film__title'),
            collection_name=F('collection__name'),
            license=F('static_asset__license__name'),
            media_type=F('static_asset__source_type'),
        )
        instance_dict = instance_qs.values().get()
        instance_dict['thumbnail_url'] = (
            instance.static_asset.preview.url if instance.static_asset.preview else ''
        )
    elif isinstance(instance, Training) and instance.status == TrainingStatus.published:
        instance_qs = sender.objects.filter(id=instance.id).annotate(project=F('name'),)
        instance_dict = instance_qs.values().get()
        instance_dict['thumbnail_url'] = instance.picture_16_9.url
    elif (
        isinstance(instance, Section)
        and instance.chapter.training.status == TrainingStatus.published
    ):
        instance_qs = sender.objects.filter(id=instance.id).annotate(
            project=F('chapter__training__name'),
            chapter_name=F('chapter__name'),
            description=F('text'),
        )
        instance_dict = instance_qs.values().get()
        instance_dict['thumbnail_url'] = instance.chapter.training.picture_16_9.url
    elif isinstance(instance, Revision) and instance.is_published and instance.post.is_published:
        instance_is_latest_revision = (
            Revision.objects.filter(is_published=True, post=instance.post).latest('date_created')
            == instance
        )
        if instance_is_latest_revision:
            instance_qs = sender.objects.filter(id=instance.id).annotate(
                project=Case(
                    When(post__film__isnull=False, then=F('post__film__title')),
                    default=Value(''),
                    output_field=CharField(),
                ),
                name=F('title'),
            )
            instance_dict = instance_qs.values().get()
            instance_dict['thumbnail_url'] = instance.picture_16_9.url

    if instance_dict:
        instance_dict['model'] = sender._meta.model_name
        instance_dict['search_id'] = f'{sender._meta.model_name}_{instance.id}'

        data_to_load = json.loads(json.dumps(instance_dict, cls=DjangoJSONEncoder))

        client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
        index = client.get_index(settings.MEILISEARCH_INDEX_NAME)
        index.add_documents(data_to_load)

        # There seems to be no way in MeiliSearch v0.13 to disable adding new document
        # fields automatically to searchable attrs, so we update the settings to set them:
        index.update_settings({'searchableAttributes': SEARCHABLE_ATTRIBUTES})

        log.info(f'Added {instance} to the search index.')


# TODO(Natalia): add post_delete signal to remove deleted objects from the search index
