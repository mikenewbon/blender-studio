# Generated by Django 3.0.14 on 2021-09-16 15:10

from django.db import migrations, models


def fill_base_html_template(apps, schema_editor):
    Email = apps.get_model('emails', 'Email')
    Email.objects.update(base_html_template='emails/email.html')


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0002_subscriptionemailpreview'),
    ]

    operations = [
        migrations.AddField(
            model_name='email',
            name='base_html_template',
            field=models.CharField(blank=True, default='emails/email.html', help_text='Base template to use when rendering the HTML version of the email', max_length=255),
        ),
        migrations.RunPython(fill_base_html_template, reverse_code=migrations.RunPython.noop),
    ]