from typing import Mapping, List

from django.http.request import HttpRequest

from training.models.trainings import TrainingDifficulty, TrainingType, TrainingStatus
from training.queries import trainings


def enums(request: HttpRequest) -> Mapping[str, object]:
    """Inject the Enums into the template context."""
    return {
        'TrainingDifficulty': TrainingDifficulty,
        'TrainingType': TrainingType,
        'TrainingStatus': TrainingStatus,
    }


def favorited(request: HttpRequest) -> Mapping[str, List[int]]:
    """Inject IDs of favorite trainings into the template context."""
    favorited_ids = []
    if request.user:
        favorited_ids = [training.pk for training in trainings.favorited(user_pk=request.user.pk)]
    return {
        'FavoritedTrainingIDs': favorited_ids,
    }
