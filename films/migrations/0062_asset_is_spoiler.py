# Generated by Django 3.0.9 on 2020-12-16 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0061_show_blog_posts'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='is_spoiler',
            field=models.BooleanField(default=False),
        ),
    ]
