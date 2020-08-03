import json
from typing import List

import meilisearch
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import Model
from django.db.models.expressions import Value, F, Case, When
from django.db.models.fields import CharField
from django.db.models.functions.text import Concat

from blog.models import Post, Revision
from films.models import Film, Asset
from training.models import Training, Section, TrainingStatus


def create_index() -> meilisearch.index.Index:
    client = meilisearch.Client('http://127.0.0.1:7700')
    index = client.create_index('studio', {'primaryKey': 'search_id'})
    index.update_settings(
        {
            'searchableAttributes': [
                # Model fields that are searchable:
                #     Film: ['model', 'title', 'description', 'summary'],
                #     Asset: ['model', 'name', 'project', 'collection_name', 'description'],
                #     Training: ['model', 'name', 'description', 'summary'],
                #     Section: ['model', 'name', 'project', 'chapter_name', 'text'],
                #     Post: ['model', 'title', 'project', 'topic', 'description', 'content']
                # In the order of relevance:
                'model',
                'title',
                'name',
                'project',
                'topic',
                'collection_name',
                'chapter_name',
                'description',
                'summary',
                'text',
                'content',
            ],
            'acceptNewFields': False,
        }
    )
    index.update_attributes_for_faceting(['model', 'project'])

    return index


def add_documents() -> None:
    client = meilisearch.Client('http://127.0.0.1:7700')
    index = client.get_index('studio')

    models_and_querysets = {
        Film: Film.objects.filter(is_published=True),
        Asset: (
            Asset.objects.filter(is_published=True, film__is_published=True).annotate(
                project=F('film__title'), collection_name=F('collection__name'),
            )
        ),
        Training: Training.objects.filter(status=TrainingStatus.published),
        Section: (
            Section.objects.filter(chapter__training__status=TrainingStatus.published)
            .select_related('chapter__training')
            .annotate(project=F('chapter__training__name'), chapter_name=F('chapter__name'))
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
                )
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
    print(f'{len(objects_to_load)} objects to load')
    index.add_documents(json.loads(json.dumps(objects_to_load, cls=DjangoJSONEncoder)))
    # TODO(Natalia): Any better way to serialize datetime objects?
