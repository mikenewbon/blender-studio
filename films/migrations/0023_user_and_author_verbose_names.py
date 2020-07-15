# Generated by Django 3.0.8 on 2020-07-10 13:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('films', '0022_storage_on_delete_protect'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productionlog',
            name='author',
            field=models.ForeignKey(blank=True, help_text='The actual author of the summary in the weekly production log', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='authored_production_logs', to=settings.AUTH_USER_MODEL, verbose_name='author (optional)'),
        ),
        migrations.AlterField(
            model_name='productionlog',
            name='name',
            field=models.CharField(blank=True, help_text='If not provided, will be set to <em>"This week on [film title]"</em>.', max_length=512, verbose_name='weekly title'),
        ),
        migrations.AlterField(
            model_name='productionlog',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='uploaded_production_logs', to=settings.AUTH_USER_MODEL, verbose_name='created by'),
        ),
        migrations.AlterField(
            model_name='productionlogentry',
            name='author',
            field=models.ForeignKey(blank=True, help_text='The actual author of the assets in the production log entry', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='authored_log_entries', to=settings.AUTH_USER_MODEL, verbose_name='author (optional)'),
        ),
        migrations.AlterField(
            model_name='productionlogentry',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='uploaded_log_entries', to=settings.AUTH_USER_MODEL, verbose_name='created by'),
        ),
    ]