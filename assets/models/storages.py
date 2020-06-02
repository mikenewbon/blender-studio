from django.db import models


class StorageBackend(models.Model):
    name = models.CharField(max_length=512)

    def __str__(self):
        return self.name
