from django.db import models
from django.utils.text import slugify


class License(models.Model):
    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    description = models.TextField()
    url = models.URLField()

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self):
        return f'License: {self.name}'
