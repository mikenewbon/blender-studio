from django.db import models


class StorageLocationCategoryChoices(models.TextChoices):
    local = 'local', 'Local Storage'
    gcs = 'gcs', 'Google Cloud Storage'


class StorageLocation(models.Model):
    name = models.CharField(max_length=512)
    category = models.CharField(
        choices=StorageLocationCategoryChoices.choices,
        max_length=5,
        default=StorageLocationCategoryChoices.local,
    )
    bucket_name = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return self.name