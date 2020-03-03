from django.contrib.auth.models import User
from django.db import models

from comments.models import Comment
from common import mixins


class PostStatus(models.TextChoices):
    published = 'published', 'Published'
    unpublished = 'unpublished', 'Unpublished'


class Post(mixins.CreatedUpdatedMixin, models.Model):
    # TODO(sem): Maybe add a ForeignKey to a Profile instead? Because authors
    #            might not have an account per se.
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    slug = models.SlugField()

    status = models.TextField(choices=PostStatus.choices)

    comments = models.ManyToManyField(Comment, through='PostComment', related_name='post')


class RevisionStatus(models.TextChoices):
    published = 'published', 'Published'
    unpublished = 'unpublished', 'Unpublished'


class Revision(mixins.CreatedUpdatedMixin, models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='revisions')
    status = models.TextField(choices=RevisionStatus.choices)

    # We prevent deletion of the editor account to make sure we preserve all
    # accountability for revisions.
    editor = models.ForeignKey(User, on_delete=models.PROTECT)
    title = models.CharField(max_length=512)
    text = models.TextField()


class PostComment(models.Model):
    class Meta:
        constraints = [models.UniqueConstraint(fields=['comment'], name='unique_post_per_comment')]

    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
