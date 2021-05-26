from django.conf import settings
from django.db import migrations


form_description = {
    'bank': 'When choosing to pay by bank, you will be required to manually perform payments and the subscription will be activated only when we receive the funds.',
    'braintree': 'Automatic charges',
}
frontend_names = {
    'bank': 'Bank Transfer',
    'braintree': 'Credit Card or PayPal',
}


def add_gateways(apps, schema_editor):
    Gateway = apps.get_model('looper', 'Gateway')

    for (name, _) in Gateway._meta.get_field('name').choices:
        if name == 'mock':
            continue
        Gateway.objects.get_or_create(
            name=name,
            frontend_name=frontend_names.get(name),
            is_default=name.lower() == 'braintree',
            form_description=form_description.get(name),
        )


def remove_gateways(apps, schema_editor):
    # Allow reverting this migration when in DEBUG mode only
    if not settings.DEBUG:
        return

    Gateway = apps.get_model('looper', 'Gateway')
    Gateway.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_gateways, reverse_code=remove_gateways),
    ]
