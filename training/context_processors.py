from typing import Mapping, List

from django.http.request import HttpRequest

from training.models.trainings import TrainingDifficulty, TrainingType
from training.queries import trainings


def enums(request: HttpRequest) -> Mapping[str, object]:
    """Inject the Enums into the template context."""
    return {
        'TrainingDifficulty': TrainingDifficulty,
        'TrainingType': TrainingType,
    }


def favorited(request: HttpRequest) -> Mapping[str, List[int]]:
    """Inject IDs of favorite trainings into the template context."""
    favorited_training_ids = []
    if getattr(request, 'user', None) and request.user.is_authenticated:
        favorited_training_ids = [
            training.pk for training in trainings.favorited(user_pk=request.user.pk)
        ]
    return {
        'favorited_training_ids': favorited_training_ids,
    }
