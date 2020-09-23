from typing import Optional, Union, Sequence

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from comments.models import Comment
from common import mixins, markdown
from common.upload_paths import get_upload_to_hashed_path
from films.models import Film
from static_assets.models import StorageLocation


class Post(mixins.CreatedUpdatedMixin, models.Model):
    film = models.ForeignKey(
        Film, blank=True, null=True, on_delete=models.CASCADE, related_name='posts'
    )
    # TODO(sem): Maybe add a ForeignKey to a Profile instead? Because authors
    #            might not have an account per se.
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='authored_posts')
    slug = models.SlugField()

    is_published = models.BooleanField(default=False)

    comments = models.ManyToManyField(Comment, through='PostComment', related_name='post')

    def __str__(self):
        return f'Post "{self.slug}" by {self.author}'

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return reverse('post-detail', kwargs={'post_slug': self.slug})

    @property
    def comment_url(self) -> str:
        return reverse('api-post-comment', kwargs={'post_pk': self.pk},)

    @property
    def admin_url(self) -> str:
        return reverse('admin:blog_post_change', args=[self.pk])


class Revision(mixins.CreatedUpdatedMixin, models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='revisions')

    # We prevent deletion of the editor account to make sure we preserve all
    # accountability for revisions.
    editor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='edited_posts')
    title = models.CharField(max_length=512)
    topic = models.CharField(max_length=128)
    description = models.TextField(
        blank=True, help_text='An optional short description displayed on the blog card.'
    )
    content = models.TextField()
    html_content = models.TextField(blank=True, editable=False)
    storage_location = models.ForeignKey(
        StorageLocation, on_delete=models.PROTECT, related_name='revisions'
    )
    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path)

    is_published = models.BooleanField(default=False)

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Union[Sequence[str], str]] = None,
    ) -> None:
        """Generates the html version of the content and saves the object."""
        self.html_content = markdown.render(self.content)
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return f'Revision "{self.title}" by {self.editor}, {self.date_created:%d %B %Y %H:%M}'

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return self.post.url

    @property
    def admin_url(self) -> str:
        return reverse('admin:blog_post_change', args=[self.post.pk])


class PostComment(models.Model):
    """An intermediary model between Post and Comment.

    A PostComment should in fact only relate to one Comment, hence the
    OneToOne comment field.
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    comment = models.OneToOneField(Comment, on_delete=models.CASCADE)
