from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.urls.base import reverse
from django.utils import timezone
from django.utils.text import slugify
from taggit.managers import TaggableManager

from comments.models import Comment
from common import mixins
from films.models import Collection
import common.help_texts
import static_assets.models as models_static_assets

User = get_user_model()


class AssetCategory(models.TextChoices):
    artwork = 'artwork', 'Artwork'
    production_file = 'production_file', 'Production File'
    production_lesson = 'production_lesson', 'Production Lesson'


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    """This represents the leaf of the tree of film-related resources.

    An asset can be of one of the three types: image, video, or file.
    """

    class Meta:
        ordering = ['order', 'date_published']

    date_published = models.DateTimeField(default=timezone.now)
    film = models.ForeignKey('Film', on_delete=models.CASCADE, related_name='assets')
    static_asset = models.ForeignKey(
        'static_assets.StaticAsset',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='assets',
    )

    collection = models.ForeignKey(
        Collection, blank=True, null=True, on_delete=models.SET_NULL, related_name='assets'
    )
    order = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True, help_text=common.help_texts.markdown_with_html)
    category = models.CharField(choices=AssetCategory.choices, max_length=17, db_index=True)
    view_count = models.PositiveIntegerField(default=0, editable=False)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    is_spoiler = models.BooleanField(default=False)
    contains_blend_file = models.BooleanField(
        default=False, help_text='Is the asset a .blend file or a package containing .blend files?'
    )
    attachments = models.ManyToManyField(
        models_static_assets.StaticAsset, blank=True, related_name='+'
    )

    comments = models.ManyToManyField(Comment, through='AssetComment', related_name='asset')
    tags = TaggableManager(blank=True)

    def clean(self) -> None:
        # TODO(fsiddi) Add background job to update file metadata for static_asset on the bucket
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)[:50]
        if self.collection and self.collection.film != self.film:
            raise ValidationError('Collection\'s film does not match the asset\'s film.')

    def __str__(self) -> str:
        return (
            f'{self.film}: {self.name}'
            f'{self.is_free and " 🆓" or ""}{self.is_featured and " ★" or ""}'
        )

    @property
    def size_bytes(self) -> int:
        if not self.static_asset:
            return 0
        if self.static_asset.source_type == 'video':
            variation = self.static_asset.video.variations.first()
            if not variation:
                return self.static_asset.size_bytes
            return variation.size_bytes
        else:
            return self.static_asset.size_bytes

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        """Returns link to asset in collection or in Featured Gallery.

        The primary place where assets are displayed is collections in film gallery.
        Some assets (e.g. films) do not belong to collections, but are displayed as featured.
        If none of the above conditions applies, the asset is probably not available anywhere
        on the website, and the url property returns an empty string.
        """
        if self.is_featured:
            gallery_url = reverse('film-gallery', kwargs={'film_slug': self.film.slug})
            return f'{gallery_url}?asset={self.pk}'
        if self.collection:
            collection_url = reverse(
                'collection-detail',
                kwargs={'film_slug': self.film.slug, 'collection_slug': self.collection.slug},
            )
            return f'{collection_url}?asset={self.pk}'
        return ''

    @property
    def comment_url(self) -> str:
        return reverse('api-asset-comment', kwargs={'asset_pk': self.pk})

    @property
    def admin_url(self) -> str:
        return reverse('admin:films_asset_change', args=[self.pk])

    @property
    def like_url(self) -> str:
        return reverse('api-asset-like', kwargs={'asset_pk': self.pk})


class AssetComment(models.Model):
    """This is an intermediary model between Asset and Comment.

    An AssetComment should in fact only relate to one Comment, hence the
    OneToOne comment field.
    """

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    comment = models.OneToOneField(Comment, on_delete=models.CASCADE)


class Like(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'asset'], name='only_one_like_per_asset_and_user'
            )
        ]

    # Whenever a User is deleted their Like lives on to ensure integrity of the conversation.
    # Instead, we remove the reference to the User to honor the deletion request as much as
    # possible.
    user = models.ForeignKey(
        User, null=True, blank=False, on_delete=models.SET_NULL, related_name='liked_assets'
    )
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='likes')

    def __str__(self) -> str:
        return f'Like by {self.username} on {self.asset}'

    @property
    def username(self) -> str:
        return '<deleted>' if self.user is None else self.user.username
