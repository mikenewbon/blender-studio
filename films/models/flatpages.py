from typing import Any

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from common import mixins, markdown
import common.help_texts
import static_assets.models as models_static_assets
from films.models import Film


class FilmFlatPage(mixins.CreatedUpdatedMixin, models.Model):
    """Stores a single film-related flat page."""

    class Meta:
        constraints = [
            # The slug and film slug are used in the page url, which has to be unique.
            models.UniqueConstraint(fields=['slug', 'film'], name='unique_film_flat_page_url'),
        ]

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='flatpages')
    title = models.CharField(
        'Page title',
        max_length=50,
        help_text='It will be displayed as the section name in the navigation bar.',
    )
    slug = models.SlugField(
        'Page slug',
        blank=True,
        help_text=(
            'The page slug has to be unique per film. '
            'If it is not filled, it will be the slugified page title.'
        ),
    )
    content = models.TextField(blank=True, help_text=common.help_texts.markdown_with_html)
    content_html = models.TextField(blank=True, editable=False)
    attachments = models.ManyToManyField(models_static_assets.StaticAsset, blank=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generates the html version of the content and saves the object."""
        if not self.slug:
            self.slug = slugify(self.title)
        # Clean but preserve some of the HTML tags
        self.content = markdown.clean(self.content)
        self.content_html = markdown.render_unsafe(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Flat page "{self.title}" of the film {self.film.title}'

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return reverse(
            'film-flatpage', kwargs={'film_slug': self.film.slug, 'page_slug': self.slug}
        )

    @property
    def admin_url(self) -> str:
        return reverse('admin:films_filmflatpage_change', args=[self.pk])
