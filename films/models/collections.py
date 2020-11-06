from django.db import models
from django.urls.base import reverse
from django.utils.text import slugify
from django.contrib.auth.models import User

from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from films.models import films
import common.help_texts


class ThumbnailAspectRatioChoices(models.TextChoices):
    original = 'original', 'Original'
    square = '1:1', 'Square (1:1)'
    widescreen = '16:9', 'Widescreen (16:9)'
    four_by_three = '4:3', 'Four-By-Three (4:3)'


class Collection(mixins.CreatedUpdatedMixin, mixins.StaticThumbnailURLMixin, models.Model):
    class Meta:
        ordering = ['order', 'date_created']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'slug'], name='unique_slug_per_collection'),
        ]

    film = models.ForeignKey(films.Film, on_delete=models.CASCADE, related_name='collections')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='child_collections'
    )
    order = models.IntegerField(null=True, blank=True)

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    text = models.TextField(blank=True, help_text=common.help_texts.markdown)
    # TODO(fsiddi) Add text_html

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path, blank=True, null=True)
    thumbnail_aspect_ratio = models.CharField(
        choices=ThumbnailAspectRatioChoices.choices,
        max_length=10,
        default=ThumbnailAspectRatioChoices.original,
        help_text='Controls aspect ratio of the thumbnails shown in the gallery.',
    )

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self):
        order = self.order or '-'
        return f'{self.film.title}: ({order}) {self.name}'

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return reverse(
            'collection-detail', kwargs={'film_slug': self.film.slug, 'collection_slug': self.slug}
        )

    @property
    def admin_url(self) -> str:
        return reverse('admin:films_collection_change', args=[self.pk])
