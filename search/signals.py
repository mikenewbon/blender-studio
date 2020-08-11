import json
import logging
from typing import Type, Any

import meilisearch
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save
from django.dispatch import receiver

from blog.models import Revision
from films.models import Film, Asset
from search.management.commands.create_search_index import SEARCHABLE_ATTRIBUTES
from search.queries import (
    SearchableModels,
    get_searchable_queryset,
)
from training.models import Training, Section

log = logging.getLogger(__name__)


@receiver(post_save, sender=Film)
@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Training)
@receiver(post_save, sender=Section)
@receiver(post_save, sender=Revision)
def update_search_index(
    sender: Type[SearchableModels], instance: SearchableModels, **kwargs: Any
) -> None:
    instance_qs = get_searchable_queryset(sender)
    if instance_qs:
        instance_dict = instance_qs.values().get()

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
