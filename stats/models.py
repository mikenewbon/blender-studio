from django.db import models


class Sample(models.Model):
    class Meta:
        ordering = ['timestamp']
        db_table = 'stats'

    timestamp = models.DateTimeField()
    comments_count = models.PositiveIntegerField(blank=True, null=True)
    film_assets_count = models.PositiveIntegerField(blank=True, null=True)
    blog_posts_count = models.PositiveIntegerField(blank=True, null=True)
    users_total_count = models.PositiveIntegerField(blank=True, null=True)
    users_subscribers_count = models.PositiveIntegerField(blank=True, null=True)
    users_demo_count = models.PositiveIntegerField(blank=True, null=True)
    training_seconds = models.PositiveIntegerField(blank=True, null=True)
    legacy_id = models.SlugField(blank=True)
