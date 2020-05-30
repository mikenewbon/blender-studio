# Generated by Django 3.0.4 on 2020-05-29 14:48

import assets.models.assets
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('films', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order', models.IntegerField()),
                ('name', models.CharField(max_length=512)),
                ('slug', models.SlugField(blank=True)),
                ('text', models.TextField()),
                ('category', models.CharField(choices=[('artwork', 'Artwork'), ('production_file', 'Production File'), ('production_lesson', 'Production Lesson')], db_index=True, max_length=17)),
                ('view_count', models.PositiveIntegerField()),
                ('visibility', models.BooleanField(default=False)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='authored_assets', to=settings.AUTH_USER_MODEL)),
                ('collection', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets', to='films.Collection')),
                ('film', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='films.Film')),
            ],
        ),
        migrations.CreateModel(
            name='License',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=512)),
                ('slug', models.SlugField(blank=True)),
                ('description', models.TextField()),
                ('url', models.URLField()),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(upload_to=assets.models.assets.get_upload_to_hashed_path)),
                ('size_bytes', models.IntegerField()),
                ('resolution', models.CharField(blank=True, max_length=32)),
                ('resolution_text', models.CharField(blank=True, max_length=32)),
                ('duration_seconds', models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')),
                ('preview', models.ImageField(upload_to=assets.models.assets.get_upload_to_hashed_path)),
                ('play_count', models.PositiveIntegerField()),
                ('asset', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='assets.Asset')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('file', models.ImageField(upload_to=assets.models.assets.get_upload_to_hashed_path)),
                ('size_bytes', models.IntegerField()),
                ('resolution', models.CharField(blank=True, max_length=32)),
                ('resolution_text', models.CharField(blank=True, max_length=32)),
                ('asset', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='assets.Asset')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('file', models.FileField(upload_to=assets.models.assets.get_upload_to_hashed_path)),
                ('size_bytes', models.IntegerField()),
                ('preview', models.ImageField(upload_to=assets.models.assets.get_upload_to_hashed_path)),
                ('asset', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='assets.Asset')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='asset',
            name='license',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets', to='assets.License'),
        ),
        migrations.AddField(
            model_name='asset',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='uploaded_assets', to=settings.AUTH_USER_MODEL),
        ),
    ]