from typing import Mapping

from django.http.request import HttpRequest

from training.models.trainings import TrainingDifficulty, TrainingType, TrainingStatus


def enums(request: HttpRequest) -> Mapping[str, object]:
    """Inject the Enums into the template context."""
    return {
        'TrainingDifficulty': TrainingDifficulty,
        'TrainingType': TrainingType,
        'TrainingStatus': TrainingStatus,
    }
