from django.db import models
from django.urls.base import reverse
from django.utils.text import slugify
from taggit.managers import TaggableManager

from comments.models import Comment
from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from training.models import chapters


class Section(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        # TODO(fsiddi) Replace these constraints, which are not valid anymore
        constraints = [
            models.UniqueConstraint(fields=['chapter', 'index'], name='unique_index_per_section'),
            models.UniqueConstraint(fields=['chapter', 'slug'], name='unique_slug_per_section'),
        ]

    chapter = models.ForeignKey(chapters.Chapter, on_delete=models.CASCADE, related_name='sections')
    index = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
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

    comments = models.ManyToManyField(Comment, through='SectionComment', related_name='section')
    tags = TaggableManager(blank=True)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            # TODO(fsiddi) Either turn slug into alphaid, or ensure uniqueness of slug
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return (
            f'{self.chapter.training.name} > {self.chapter.index:02.0f}. {self.chapter.name} > '
            f'{self.index:02.0f}. {self.name}'
        )

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
