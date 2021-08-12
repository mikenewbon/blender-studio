from django.db import models


class Sample(models.Model):
    class Meta:
        ordering = ['timestamp']
        db_table = 'stats'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['timestamp', 'slug', 'value']),
        ]

    timestamp = models.DateTimeField(auto_now_add=True)
    # Should not be null, but was required by the migration
    slug = models.SlugField(null=True, blank=True)
    value = models.PositiveIntegerField(default=0)
    legacy_id = models.SlugField(null=True, blank=True)
