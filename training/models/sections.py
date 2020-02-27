from __future__ import annotations

from pathlib import Path

from django.db import models
from django.urls.base import reverse
from django.utils.text import slugify

from comments.models import Comment
from common import mixins
from training.models import chapters


class Section(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['chapter', 'index'], name='unique_index_per_section'),
        ]

    chapter = models.ForeignKey(chapters.Chapter, on_delete=models.CASCADE, related_name='sections')
    index = models.IntegerField()

    name = models.TextField(unique=True)
    slug = models.SlugField(unique=True, blank=True)
    text = models.TextField()

    comments = models.ManyToManyField(Comment, through='SectionComment', related_name='section')

    def clean(self) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return f'{self.chapter.training.name} > {self.chapter.index:02.0f}. {self.chapter.name} > {self.index:02.0f}. {self.name}'

    @property
    def url(self) -> str:
        return reverse(
            'section',
            kwargs={
                'training_slug': self.chapter.training.slug,
                'chapter_index': self.chapter.index,
                'chapter_slug': self.chapter.slug,
                'section_index': self.index,
                'section_slug': self.slug,
            },
        )

    @property
    def comment_url(self) -> str:
        return reverse('section_comment', kwargs={'section_pk': self.pk},)

    @property
    def progress_url(self) -> str:
        return reverse('section_progress', kwargs={'section_pk': self.pk})


class SectionComment(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['comment'], name='unique_section_per_comment')
        ]

    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)


def video_upload_path(video: Video, filename: str) -> str:
    return str(
        Path('trainings')
        / str(video.section.chapter.training.id)
        / 'chapters'
        / str(video.section.chapter.index)
        / 'sections'
        / str(video.section.index)
        / 'video'
        / filename
    )


class Video(mixins.CreatedUpdatedMixin, models.Model):
    section = models.OneToOneField(Section, on_delete=models.CASCADE, related_name='video')
    file = models.FileField(upload_to=video_upload_path)
    size = models.IntegerField()
    duration = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')

    def __str__(self) -> str:
        return self.file.path  # type: ignore

    @property
    def progress_url(self) -> str:
        return reverse('video_progress', kwargs={'video_pk': self.pk})


def asset_upload_path(asset: Asset, filename: str) -> str:
    return str(
        Path('trainings')
        / str(asset.section.chapter.training.id)
        / 'chapters'
        / str(asset.section.chapter.index)
        / 'sections'
        / str(asset.section.index)
        / 'assets'
        / filename
    )


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='assets')
    file = models.FileField(upload_to=asset_upload_path)
    size = models.IntegerField()

    def __str__(self) -> str:
        return self.file.path  # type: ignore
