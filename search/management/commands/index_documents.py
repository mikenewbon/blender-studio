import json
from typing import List
from typing import Optional, Any

import meilisearch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import Model
from django.db.models.expressions import Value, F, Case, When
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat

from blog.models import Post, Revision
from films.models import Film, Asset
from search.management.commands.create_search_index import SEARCHABLE_ATTRIBUTES
from training.models import Training, Section, TrainingStatus


class Command(BaseCommand):
    help = (
        f'Add database objects to the search index "{settings.MEILISEARCH_INDEX_NAME}". '
        f'Indexes the following models: Film, Asset, Training, Section, Post. '
        f'If an object already exists in the index, it is updated.'
    )

    def prepare_data(self) -> Any:
        self.stdout.write('Preparing the data, it may take a while...')

        models_and_querysets = {
            Film: Film.objects.filter(is_published=True).annotate(
                project=F('title'), name=F('title'),
            ),
            Asset: (
                Asset.objects.filter(is_published=True, film__is_published=True)
                .select_related('static_asset')
                .annotate(
                    project=F('film__title'),
                    collection_name=F('collection__name'),
                    license=F('static_asset__license__name'),
                    media_type=F('static_asset__source_type'),
                )
            ),
            Training: Training.objects.filter(status=TrainingStatus.published).annotate(
                project=F('name'),
            ),
            Section: (
                Section.objects.filter(chapter__training__status=TrainingStatus.published)
                .select_related('chapter__training')
                .annotate(
                    project=F('chapter__training__name'),
                    chapter_name=F('chapter__name'),
                    description=F('text'),
                )
            ),
            Post: (
                Revision.objects.filter(is_published=True, post__is_published=True)
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
            ),
        }

        objects_to_load: List[Model] = []
        for model, queryset in models_and_querysets.items():
            queryset = queryset.annotate(
                model=Value(model._meta.model_name, output_field=CharField()),
                search_id=Concat('model', Value('_'), 'id', output_field=CharField()),
            )
            qs_values = queryset.values()

            for obj, obj_dict in zip(queryset, qs_values):
                if model == Film:
                    obj_dict['thumbnail_url'] = (
                        obj.picture_16_9.url if obj.picture_16_9 else obj.picture_header.url
                    )
                elif model == Asset:
                    obj_dict['thumbnail_url'] = (
                        obj.static_asset.preview.url if obj.static_asset.preview else ''
                    )
                elif model in [Training, Post]:
                    obj_dict['thumbnail_url'] = obj.picture_16_9.url
                elif model == Section:
                    obj_dict['thumbnail_url'] = obj.chapter.training.picture_16_9.url

            objects_to_load.extend(qs_values)

        self.stdout.write(f'{len(objects_to_load)} objects to load')

        # TODO(Natalia): Any better way to serialize datetime objects?
        return json.loads(json.dumps(objects_to_load, cls=DjangoJSONEncoder))

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        client = meilisearch.Client(settings.MEILISEARCH_API_ADDRESS)
        index = client.get_index(settings.MEILISEARCH_INDEX_NAME)

        data_to_load = self.prepare_data()

        try:
            index.add_documents(data_to_load)
        except meilisearch.errors.MeiliSearchCommunicationError:
            raise CommandError(
                f'Failed to establish a new connection with MeiliSearch API at '
                f'{settings.MEILISEARCH_API_ADDRESS}. Make sure that the server is running.'
            )
        except meilisearch.errors.MeiliSearchApiError:
            raise CommandError(
                f'Error accessing the index "{settings.MEILISEARCH_INDEX_NAME}" of the client '
                f'at {self.MEILISEARCH_API_ADDRESS}. Make sure that the index exists.'
            )

        # There seems to be no way in MeiliSearch v0.13 to disable adding new document
        # fields automatically to searchable attrs, so we update the settings to set them:
        index.update_settings({'searchableAttributes': SEARCHABLE_ATTRIBUTES})

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated the index "{settings.MEILISEARCH_INDEX_NAME}".'
            )
        )

        return None
