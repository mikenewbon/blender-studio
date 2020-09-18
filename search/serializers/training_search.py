from taggit.models import Tag

from search.serializers.base import BaseSearchSerializer
from training.models import Training, TrainingStatus


class TrainingSearchSerializer(BaseSearchSerializer):
    """Prepare database objects to be indexed in the training search index."""

    models_to_index = [Training]
    filter_params = {
        Training: {'status': TrainingStatus.published},
    }
    annotations = {
        Training: {},
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
    }
