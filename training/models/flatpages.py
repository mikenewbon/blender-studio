"""Custom flat pages for training."""
from typing import Any

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from common import mixins, markdown
from common.upload_paths import get_upload_to_hashed_path
from training.models import Training
import common.help_texts
import static_assets.models as models_static_assets


class TrainingFlatPage(mixins.CreatedUpdatedMixin, mixins.StaticThumbnailURLMixin, models.Model):
    """Stores a single training-related flat page."""

    class Meta:  # noqa: D106
        constraints = [
            # The slug and training slug are used in the page url, which has to be unique.
            models.UniqueConstraint(
                fields=['slug', 'training'], name='unique_training_flat_page_url'
            ),
        ]

    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='flatpages')
    title = models.CharField(
        'Page title',
        max_length=50,
        help_text='It will be displayed as the section name in the navigation bar.',
    )
    slug = models.SlugField(
        'Page slug',
        blank=True,
        help_text=(
            'The page slug has to be unique per training. '
            'If it is not filled, it will be the slugified page title.'
        ),
    )
    content = models.TextField(blank=True, help_text=common.help_texts.markdown_with_html)
    content_html = models.TextField(blank=True, editable=False)
    attachments = models.ManyToManyField(models_static_assets.StaticAsset, blank=True)
    header = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generate the html version of the content and saves the object."""
        if not self.slug:
            self.slug = slugify(self.title)
        # Clean but preserve some of the HTML tags
        self.content = markdown.clean(self.content)
        self.content_html = markdown.render_unsafe(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Flat page "{self.title}" of the training {self.training.name}'

    @property
    def thumbnail(self):
        """Make static thumbnails mixin work."""
        return self.header

    def get_absolute_url(self) -> str:  # noqa: D102
        return self.url

    @property
    def url(self) -> str:  # noqa: D102
        return reverse(
            'training-flatpage',
            kwargs={'training_slug': self.training.slug, 'page_slug': self.slug},
        )

    @property
    def admin_url(self) -> str:  # noqa: D102
        return reverse('admin:training_trainingflatpage_change', args=[self.pk])
