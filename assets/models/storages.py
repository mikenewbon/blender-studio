from django.db import models

from films.models import Film
from training.models import Training


class StorageBackend(models.Model):
    name = models.CharField(max_length=512)
    film = models.OneToOneField(Film, blank=True, null=True, on_delete=models.CASCADE)
    training = models.OneToOneField(Training, blank=True, null=True, on_delete=models.CASCADE)

    # TODO: validation - either film or a training has to be null, but not both
