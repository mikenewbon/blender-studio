# Generated by Django 3.0.8 on 2020-07-09 09:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('static_assets', '0014_storage_on_delete_protect'),
        ('films', '0021_production_log_alter_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collection',
            name='storage_location',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='static_assets.StorageLocation'),
        ),
        migrations.AlterField(
            model_name='productionlog',
            name='storage_location',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='production_logs', to='static_assets.StorageLocation'),
        ),
    ]
