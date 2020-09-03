# Generated by Django 3.0.9 on 2020-08-17 19:58

from django.db import migrations
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0003_taggeditem_add_unique_index'),
        ('training', '0017_storage_on_delete_protect_and_size_bytes'),
    ]

    operations = [
        migrations.RemoveField(model_name='trainingtag', name='tag',),
        migrations.RemoveField(model_name='trainingtag', name='training',),
        migrations.AddField(
            model_name='section',
            name='tags',
            field=taggit.managers.TaggableManager(
                help_text='A comma-separated list of tags.',
                through='taggit.TaggedItem',
                to='taggit.Tag',
                verbose_name='Tags',
            ),
        ),
        migrations.AlterField(
            model_name='training',
            name='tags',
            field=taggit.managers.TaggableManager(
                help_text='A comma-separated list of tags.',
                through='taggit.TaggedItem',
                to='taggit.Tag',
                verbose_name='Tags',
            ),
        ),
        migrations.DeleteModel(name='Tag',),
        migrations.DeleteModel(name='TrainingTag',),
    ]
