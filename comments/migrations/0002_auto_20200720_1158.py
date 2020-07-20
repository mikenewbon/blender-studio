# Generated by Django 3.0.8 on 2020-07-20 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='date_deleted',
            field=models.DateTimeField(editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='message',
            field=models.TextField(null=True),
        ),
    ]
