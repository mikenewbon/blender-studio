from pathlib import Path

from django.db import models

from training_main.models import mixins, chapters


class Section(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['chapter', 'index'], name='unique_index_per_section'),
        ]

    chapter = models.ForeignKey(chapters.Chapter, on_delete=models.CASCADE, related_name='sections')
    index = models.IntegerField()

    name = models.TextField(unique=True)
    slug = models.TextField(unique=True)
    description = models.TextField()

    def __str__(self) -> str:
        return f'{self.index}. {self.name}'


class Video(mixins.CreatedUpdatedMixin, models.Model):
    section = models.OneToOneField(Section, on_delete=models.CASCADE, related_name='video')
    file = models.FileField(
        upload_to=lambda video, filename: str(
            Path('trainings')
            / video.section.chapter.training.id
            / 'chapters'
            / video.section.chapter.index
            / 'sections'
            / video.section.index
            / 'video'
            / filename
        )
    )
    size = models.IntegerField()

    def __str__(self) -> str:
        return self.file.path  # type: ignore


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='assets')
    file = models.FileField(
        upload_to=lambda asset, filename: str(
            Path('trainings')
            / asset.section.chapter.training.id
            / 'chapters'
            / asset.section.chapter.index
            / 'sections'
            / asset.section.index
            / 'assets'
            / filename
        )
    )
    size = models.IntegerField()

    def __str__(self) -> str:
        return self.file.path  # type: ignore
