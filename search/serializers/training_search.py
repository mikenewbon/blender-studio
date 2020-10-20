from django.db.models.expressions import F, Value
from django.db.models.fields import CharField
from taggit.models import Tag

from films.models import Asset, AssetCategory
from search.serializers.base import BaseSearchSerializer
from training.models import Training, TrainingStatus


class TrainingSearchSerializer(BaseSearchSerializer):
    """Prepare database objects to be indexed in the training search index."""

    models_to_index = [Training, Asset]
    filter_params = {
        Training: {'status': TrainingStatus.published},
        Asset: {
            'is_published': True,
            'film__is_published': True,
            'category': AssetCategory.production_lesson,
        },
    }
    annotations = {
        Training: {},
        Asset: {
            'project': F('film__title'),
            'type': Value(AssetCategory.production_lesson, output_field=CharField()),
        },
    }
    additional_fields = {
        Training: {
            'tags': lambda instance: [tag.name for tag in instance.tags.all()],
            'secondary_tags': lambda instance: [
                tag.name
                for tag in Tag.objects.filter(section__chapter__training__pk=instance.pk).distinct()
            ],
            'favorite_url': lambda instance: instance.favorite_url,
        },
        Asset: {'tags': lambda instance: [tag.name for tag in instance.tags.all()]},
    }
