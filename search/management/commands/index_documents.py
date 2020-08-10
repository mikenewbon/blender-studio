import json
from typing import List
from typing import Optional, Any

import meilisearch
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import Model
from django.db.models.expressions import Value, F, Case, When
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat
from django.db.models.query_utils import Q

from blog.models import Post, Revision
from films.models import Film, Asset
from static_assets.models import StaticAssetFileTypeChoices
from training.models import Training, Section, TrainingStatus


class Command(BaseCommand):
    help = (
        'Add database objects to the search index "studio". '
        'Indexes the following models: Film, Asset, Training, Section, Post. '
        'If an object already exists in the index, it is updated.'
    )

    def prepare_data(self):
        models_and_querysets = {
            Film: Film.objects.filter(is_published=True).annotate(
                project=F('title'),
                name=F('title'),
                thumbnail=Case(
                    When(~Q(picture_16_9=''), then=F('picture_16_9')), default=F('picture_header')
                ),
            ),
            Asset: (
                Asset.objects.filter(is_published=True, film__is_published=True)
                .select_related('static_asset')
                .annotate(
                    project=F('film__title'),
                    collection_name=F('collection__name'),
                    thumbnail=Case(
                        When(
                            ~Q(static_asset__source_preview=''),
                            then=F('static_asset__source_preview'),
                        ),
                        When(
                            Q(static_asset__source_type=StaticAssetFileTypeChoices.image),
                            then=F('static_asset__source'),
                        ),
                        default=Value(''),
                    ),
                )
            ),
            Training: Training.objects.filter(status=TrainingStatus.published).annotate(
                project=F('name'), thumbnail=F('picture_16_9')
            ),
            Section: (
                Section.objects.filter(chapter__training__status=TrainingStatus.published)
                .select_related('chapter__training')
                .annotate(
                    project=F('chapter__training__name'),
                    chapter_name=F('chapter__name'),
                    thumbnail=F('chapter__training__picture_16_9'),
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
                    thumbnail=F('picture_16_9'),
                )
            ),
        }

        objects_to_load: List[Model] = []
        for model, queryset in models_and_querysets.items():
            objects_to_load.extend(
                list(
                    queryset.annotate(
                        model=Value(model._meta.model_name, output_field=CharField()),
                        search_id=Concat('model', Value('_'), 'id', output_field=CharField()),
                    ).values()
                )
            )
        self.stdout.write(f'{len(objects_to_load)} objects to load')

        # TODO(Natalia): Any better way to serialize datetime objects?
        return json.loads(json.dumps(objects_to_load, cls=DjangoJSONEncoder))

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        client_address: str = 'http://127.0.0.1:7700'
        index_name: str = 'studio'

        client = meilisearch.Client(client_address)
        index = client.get_index(index_name)

        data_to_load = self.prepare_data()

        try:
            index.add_documents(data_to_load)
        except json.decoder.JSONDecodeError:
            raise CommandError(
                f'Error accessing the index {index_name} of the client at {client_address}. '
                f'Make sure that the MeiliSearch server is running and the index exists'
            )

        self.stdout.write(self.style.SUCCESS('Successfully updated the index "%s"' % index_name))
