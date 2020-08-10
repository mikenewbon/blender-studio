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

from blog.models import Post, Revision
from films.models import Film, Asset
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
                project=F('title'), name=F('title'),
            ),
            Asset: (
                Asset.objects.filter(is_published=True, film__is_published=True)
                .select_related('static_asset')
                .annotate(project=F('film__title'), collection_name=F('collection__name'),)
            ),
            Training: Training.objects.filter(status=TrainingStatus.published).annotate(
                project=F('name'),
            ),
            Section: (
                Section.objects.filter(chapter__training__status=TrainingStatus.published)
                .select_related('chapter__training')
                .annotate(project=F('chapter__training__name'), chapter_name=F('chapter__name'),)
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

            if model == Film:
                for film, film_dict in zip(queryset, qs_values):
                    film_dict['thumbnail_url'] = (
                        film.picture_16_9.url if film.picture_16_9 else film.picture_header.url
                    )
            elif model == Asset:
                for asset, asset_dict in zip(queryset, qs_values):
                    asset_dict['thumbnail_url'] = (
                        asset.static_asset.preview.url if asset.static_asset.preview else ''
                    )
            elif model in [Training, Post]:
                for obj, obj_dict in zip(queryset, qs_values):
                    obj_dict['thumbnail_url'] = obj.picture_16_9.url
            elif model == Section:
                for section, section_dict in zip(queryset, qs_values):
                    section_dict['thumbnail_url'] = section.chapter.training.picture_16_9.url

            objects_to_load.extend(qs_values)

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
