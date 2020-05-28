# Generated by Django 3.0.4 on 2020-03-13 10:42

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('looper', '0054_drop_user_foreign_keys'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256)),
                (
                    'customer',
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='organization',
                        to='looper.Customer',
                    ),
                ),
            ],
            options={'abstract': False,},
        ),
        migrations.CreateModel(
            name='SubscriptionProperties',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('seats', models.IntegerField(blank=True, null=True)),
                (
                    'plan',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='properties',
                        to='looper.Subscription',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Subscription Properties',
                'verbose_name_plural': 'Subscription Properties',
            },
        ),
        migrations.CreateModel(
            name='Subscriber',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                (
                    'customer',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='subscriber',
                        to='looper.Customer',
                    ),
                ),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='subscriber',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={'abstract': False,},
        ),
        migrations.CreateModel(
            name='OrganizationUsers',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('can_change_organization', models.BooleanField(default=False)),
                (
                    'organization',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='organization_users',
                        to='subscriptions.Organization',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='organization_users',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Organization Users',
                'verbose_name_plural': 'Organization Users',
            },
        ),
        migrations.AddField(
            model_name='organization',
            name='users',
            field=models.ManyToManyField(
                related_name='organizations',
                through='subscriptions.OrganizationUsers',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]