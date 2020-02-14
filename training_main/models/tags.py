from django.db import models

from training_main.models import mixins


class Tag(mixins.CreatedUpdatedMixin, models.Model):
    name = models.TextField(primary_key=True)

    def __str__(self) -> str:
        return self.name
