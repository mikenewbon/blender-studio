import datetime

from django.contrib.auth import get_user_model
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.urls.base import reverse
from django.utils import timezone
from django.utils.text import slugify

from comments.models import Comment
from common import mixins
from films.models import Film
import common.help_texts

User = get_user_model()


class _DownloadableMixin:
    @property
    def download_url(self) -> str:
        if not self.static_asset.source:
            return ''
        return self.static_asset.source.url

    @property
    def size_bytes(self) -> int:
        if not self.static_asset.source:
            return 0
        return self.static_asset.size_bytes

    @property
    def download_size(self) -> str:
        size_bytes = self.size_bytes
        if size_bytes:
            return filesizeformat(size_bytes)
        return ''


class BlenderVersion(models.TextChoices):
    v270 = '2.70'
    v280 = '2.80'
    v290 = '2.90'
    v300 = '3.0'


class Character(mixins.CreatedUpdatedMixin, models.Model):
    """This represents a Blender Studio character."""

    class Meta:
        ordering = ['order', '-date_published']

    date_published = models.DateTimeField(default=timezone.now)
    film = models.ForeignKey(
        Film, on_delete=models.CASCADE, related_name='characters', null=True, blank=True
    )
    order = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=512)
    slug = models.SlugField(unique=True)
    view_count = models.PositiveIntegerField(default=0, editable=False)
    is_published = models.BooleanField(default=False)

    def clean(self) -> None:
        # TODO(fsiddi) Add background job to update file metadata for static_asset on the bucket
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)[:50]

    def __str__(self) -> str:
        return self.name

    @property
    def latest_version(self) -> 'CharacterVersion':
        return self.versions.first()

    @property
    def is_new(self) -> bool:
        return self.date_published > timezone.now() - datetime.timedelta(days=7)

    def get_absolute_url(self) -> str:
        return reverse('character-detail', kwargs={'slug': self.slug})

    @property
    def admin_url(self) -> str:
        return reverse('admin:characters_character_change', args=[self.pk])

    @property
    def like_url(self) -> str:
        return reverse('api-character-like', kwargs={'character_pk': self.pk})


class CharacterVersion(mixins.CreatedUpdatedMixin, _DownloadableMixin, models.Model):
    class Meta:
        ordering = ['-number']

    date_published = models.DateTimeField(default=timezone.now)
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='versions')
    static_asset = models.ForeignKey(
        'static_assets.StaticAsset', on_delete=models.CASCADE, related_name='char_versions'
    )
    preview_youtube_link = models.URLField(null=True, blank=True)
    number = models.IntegerField()
    min_blender_version = models.CharField(
        choices=BlenderVersion.choices, max_length=5, db_index=True
    )

    description = models.TextField(blank=True, help_text=common.help_texts.markdown)
    is_published = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)

    comments = models.ManyToManyField(
        Comment, through='CharacterVersionComment', related_name='character_version'
    )

    def __str__(self) -> str:
        return f'{self.character_id and self.character.name or "Character"} v{self.number or "?"}'

    @property
    def is_new(self) -> bool:
        return self.date_published > timezone.now() - datetime.timedelta(days=7)

    def get_absolute_url(self) -> str:
        return reverse(
            'character-version-detail',
            kwargs={'slug': self.character.slug, 'number': self.number},
        )

    @property
    def comment_url(self) -> str:
        return reverse(
            'api-character-version-comment',
            kwargs={'character_version_pk': self.pk},
        )


class CharacterShowcase(mixins.CreatedUpdatedMixin, _DownloadableMixin, models.Model):
    class Meta:
        ordering = ['order', '-date_published']

    date_published = models.DateTimeField(default=timezone.now)
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='showcases')
    static_asset = models.ForeignKey(
        'static_assets.StaticAsset',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='char_showcase',
    )
    preview_youtube_link = models.URLField(null=True, blank=True)

    min_blender_version = models.CharField(
        choices=BlenderVersion.choices, max_length=5, db_index=True
    )
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True, help_text=common.help_texts.markdown)
    is_published = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    order = models.IntegerField(null=True, blank=True)

    comments = models.ManyToManyField(
        Comment, through='CharacterShowcaseComment', related_name='character_showcase'
    )

    def __str__(self) -> str:
        return f'Showcase "{self.title}" for {self.character_id and self.character.name}'

    @property
    def is_new(self) -> bool:
        return self.date_published > timezone.now() - datetime.timedelta(days=7)

    def get_absolute_url(self) -> str:
        return reverse(
            'character-showcase-detail',
            kwargs={'slug': self.character.slug, 'pk': self.pk},
        )

    @property
    def comment_url(self) -> str:
        return reverse(
            'api-character-showcase-comment',
            kwargs={'character_showcase_pk': self.pk},
        )


class CharacterVersionComment(models.Model):
    """This is an intermediary model between CharacterVersion and Comment.

    A CharacterVersion should in fact only relate to one Comment, hence the
    OneToOne comment field.
    """

    character_version = models.ForeignKey(CharacterVersion, on_delete=models.CASCADE)
    comment = models.OneToOneField(Comment, on_delete=models.CASCADE)


class CharacterShowcaseComment(models.Model):
    """This is an intermediary model between CharacterShowcase and Comment.

    A CharacterShowcase should in fact only relate to one Comment, hence the
    OneToOne comment field.
    """

    character_showcase = models.ForeignKey(CharacterShowcase, on_delete=models.CASCADE)
    comment = models.OneToOneField(Comment, on_delete=models.CASCADE)


class Like(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'character'], name='only_one_like_per_character_and_user'
            )
        ]

    # Whenever a User is deleted their Like lives on to ensure integrity of the conversation.
    # Instead, we remove the reference to the User to honor the deletion request as much as
    # possible.
    user = models.ForeignKey(
        User, null=True, blank=False, on_delete=models.SET_NULL, related_name='liked_characters'
    )
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='likes')

    def __str__(self) -> str:
        return f'Like by {self.username} on {self.character}'

    @property
    def username(self) -> str:
        return '<deleted>' if self.user is None else self.user.username
