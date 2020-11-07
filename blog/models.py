import datetime
from typing import Optional, Union, Sequence, Any

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

from comments.models import Comment
from common import mixins, markdown
from common.upload_paths import get_upload_to_hashed_path
from films.models import Film
import static_assets.models as models_static_assets


class Post(mixins.CreatedUpdatedMixin, mixins.StaticThumbnailURLMixin, models.Model):
    class Meta:
        ordering = ('-date_published',)

    film = models.ForeignKey(
        Film, blank=True, null=True, on_delete=models.CASCADE, related_name='posts'
    )
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='authored_posts')
    slug = models.SlugField(max_length=128)
    date_published = models.DateTimeField(blank=True, null=True)
    legacy_id = models.CharField(max_length=256, blank=True)
    is_published = models.BooleanField(default=False)

    title = models.CharField(max_length=512)
    category = models.CharField(max_length=128, blank=True)
    excerpt = models.TextField(
        blank=True, help_text='An optional short description displayed on the blog card.'
    )
    content = models.TextField()
    content_html = models.TextField(blank=True, editable=False)

    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)
    header = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)

    comments = models.ManyToManyField(Comment, through='PostComment', related_name='post')
    attachments = models.ManyToManyField(models_static_assets.StaticAsset, blank=True)

    def __str__(self):
        return self.slug

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Generates the html version of the content and saves the object."""
        if not self.slug:
            self.slug = slugify(self.title)
        self.content_html = markdown.render(self.content)
        super().save(*args, **kwargs)

    @property
    def is_new(self) -> bool:
        return self.date_published > timezone.now() - datetime.timedelta(days=7)

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return reverse('post-detail', kwargs={'slug': self.slug})

    @property
    def comment_url(self) -> str:
        return reverse('api-post-comment', kwargs={'post_pk': self.pk})

    @property
    def admin_url(self) -> str:
        return reverse('admin:blog_post_change', args=[self.pk])


class PostComment(models.Model):
    """An intermediary model between Post and Comment.

    A PostComment should in fact only relate to one Comment, hence the
    OneToOne comment field.
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    comment = models.OneToOneField(Comment, on_delete=models.CASCADE)
