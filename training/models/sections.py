import uuid
from typing import Optional
from django.db import models
from django.urls.base import reverse
from django.contrib.auth.models import User
from taggit.managers import TaggableManager

from comments.models import Comment
from common import mixins
from training.models import chapters


class Section(mixins.CreatedUpdatedMixin, mixins.StaticThumbnailURLMixin, models.Model):
    class Meta:
        ordering = ['index', 'name']

    chapter = models.ForeignKey(chapters.Chapter, on_delete=models.CASCADE, related_name='sections')
    index = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(unique=True, null=False)
    text = models.TextField()
    is_free = models.BooleanField(default=False)

    # Can be a video, an image or a file
    # If the static asset is a video, a video player will be shown
    static_asset = models.OneToOneField(
        'static_assets.StaticAsset',
        on_delete=models.CASCADE,
        related_name='section',
        blank=True,
        null=True,
    )
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    comments = models.ManyToManyField(Comment, through='SectionComment', related_name='section')
    tags = TaggableManager(blank=True)

    def clean(self) -> None:
        super().clean()
        # TODO(fsiddi) Add background job to update file metadata for static_asset on the bucket
        if not self.slug:
            # TODO(fsiddi) Look into alphaid for a shorter slug
            self.slug = uuid.uuid4().hex

    def __str__(self) -> str:
        return (
            f'{self.chapter.training.name} > {self.chapter.index:02.0f}. {self.chapter.name} > '
            f'{self.index:02.0f}. {self.name}'
        )

    @property
    def thumbnail(self) -> Optional[str]:
        # Try to use asset thumbnail
        if self.static_asset and self.static_asset.preview:
            return self.static_asset.preview
        # Try to use chapter thumbnail
        if self.chapter.thumbnail:
            return None

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return reverse(
            'section',
            kwargs={'training_slug': self.chapter.training.slug, 'section_slug': self.slug},
        )

    @property
    def comment_url(self) -> str:
        return reverse('section-comment', kwargs={'section_pk': self.pk},)

    @property
    def progress_url(self) -> str:
        return reverse('section-progress', kwargs={'section_pk': self.pk})

    @property
    def admin_url(self) -> str:
        return reverse('admin:training_section_change', args=[self.pk])


class SectionComment(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['comment'], name='unique_section_per_comment')
        ]

    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
