# Generated by Django 3.0.9 on 2020-11-05 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('films', '0048_auto_20201105_1235'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='thumbnail_aspect_ratio',
            field=models.CharField(choices=[('original', 'Original'), ('1:1', 'Square (1:1)'), ('16:9', 'Widescreen (16:9)'), ('4:3', 'Four-By-Three (4:3)')], default='original', help_text='Controls aspect ratio of the thumbnails shown in the gallery.', max_length=10),
        ),
    ]