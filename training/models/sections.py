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

    comments = models.ManyToManyField(Comment, through='SectionComment', related_name='section')
    tags = TaggableManager(blank=True)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
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
            kwargs={'training_slug': self.chapter.training.slug, 'section_slug': self.slug,},
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


class Video(mixins.CreatedUpdatedMixin, models.Model):
    section = models.OneToOneField(Section, on_delete=models.CASCADE, related_name='video')
    file = models.FileField(upload_to=get_upload_to_hashed_path)
    size_bytes = models.BigIntegerField(editable=False)
    duration = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    duration.description = 'Video duration in the format [DD] [[HH:]MM:]ss[.uuuuuu]'

    def __str__(self) -> str:
        return self.file.name  # type: ignore

    @property
    def progress_url(self) -> str:
        return reverse('video-progress', kwargs={'video_pk': self.pk})

    def clean(self):
        super().clean()
        if self.file:
            self.size_bytes = self.file.size


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='assets')
    file = models.FileField(upload_to=get_upload_to_hashed_path)
    size_bytes = models.IntegerField(editable=False)

    def __str__(self) -> str:
        return self.file.name  # type: ignore

    def clean(self):
        super().clean()
        if self.file:
            self.size_bytes = self.file.size
