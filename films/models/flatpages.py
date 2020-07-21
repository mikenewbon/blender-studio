from django.db import models

from common import mixins, markdown
from films.models import Film


class FilmFlatPage(mixins.CreatedUpdatedMixin, models.Model):
    """
    A customised flat page model for film-related pages.

    It is heavily inspired by the django.contrib.flatpages.models.FlatPage model,
    but without the unnecessary fields and with a few additional ones instead.
    """

    class Meta:
        constraints = [
            # The slug and film slug are used in the page url, which has to be unique.
            models.UniqueConstraint(fields=['slug', 'film'], name='unique_film_flat_page_url'),
        ]

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='flatpages')

    slug = models.SlugField(
        'Page slug',
        help_text='The page slug has to be unique per film. It may be the "type" of a film page, e.g. "about".',
    )
    content = models.TextField(
        blank=True,
        help_text='Format the content in <a href="https://commonmark.org/help/">Markdown</a>.',
    )
    html_content = models.TextField(blank=True, editable=False)

    def save(self, *args, **kwargs) -> None:
        self.html_content = markdown.render(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Flat page "{self.slug}" of {self.film.title}'
