# Generated by Django 3.0.9 on 2020-10-23 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0010_extend_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='date_published',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
