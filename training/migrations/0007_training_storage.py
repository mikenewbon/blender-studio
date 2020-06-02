# Generated by Django 3.0.4 on 2020-06-02 17:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0001_initial'),
        ('training', '0006_update_unique_constraints'),
    ]

    operations = [
        migrations.AddField(
            model_name='training',
            name='storage',
            field=models.OneToOneField(default=2, on_delete=django.db.models.deletion.PROTECT, to='assets.StorageBackend'),
            preserve_default=False,
        ),
    ]
