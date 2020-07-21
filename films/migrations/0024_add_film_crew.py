# Generated by Django 3.0.8 on 2020-07-21 16:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('films', '0023_user_and_author_verbose_names'),
    ]

    operations = [
        migrations.CreateModel(
            name='FilmCrew',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('role', models.CharField(max_length=128)),
                (
                    'film',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='films.Film'),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={'unique_together': {('user', 'film')},},
        ),
        migrations.AddField(
            model_name='film',
            name='crew',
            field=models.ManyToManyField(through='films.FilmCrew', to=settings.AUTH_USER_MODEL),
        ),
    ]
