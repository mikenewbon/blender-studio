from django.db import models


class StorageBackendCategoryChoices(models.TextChoices):
    local = 'local', 'Local Storage'
    gcs = 'gcs', 'Google Cloud Storage'


class StorageBackend(models.Model):
    name = models.CharField(max_length=512)
    category = models.CharField(
        choices=StorageBackendCategoryChoices.choices,
        max_length=5,
        default=StorageBackendCategoryChoices.local,
    )
    bucket_name = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return self.name
