# Generated by Django 3.0.4 on 2020-06-23 08:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('films', '0022_verbose_names_in_production_logs'),
    ]

    operations = [
        migrations.RenameField(
            model_name='productionlog',
            old_name='description',
            new_name='summary',
        ),
        migrations.AddField(
            model_name='productionlog',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='authored_production_logs', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='productionlog',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='uploaded_production_logs', to=settings.AUTH_USER_MODEL),
        ),
    ]