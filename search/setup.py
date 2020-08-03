import meilisearch
from django.db.models.expressions import Value
from django.db.models.functions.text import Concat

from films.models import Film, Asset
from training.models import Training


def create_index() -> meilisearch.index.Index:
    client = meilisearch.Client('http://127.0.0.1:7700')
    return client.create_index('studio', {'primaryKey': 'search_id'})


def add_documents() -> None:
    client = meilisearch.Client('http://127.0.0.1:7700')
    index = client.get_index('studio')

    models_to_index = {
        Film: ['title', 'description', 'summary'],
        Training: ['name', 'description', 'summary'],
        Asset: ['name', 'collection__name', 'description'],
    }

    for model, fields in models_to_index.items():
        instances = model.objects.annotate(
            search_id=Concat(Value(model._meta.model_name), Value('_'), 'id')
        ).values('search_id', *fields)

        index.add_documents(list(instances))
