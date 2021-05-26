from django.conf import settings
from django.db import migrations


def create_customers(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    Customer = apps.get_model('looper', 'Customer')

    for user in User.objects.all():
        Customer.objects.get_or_create(
            user_id=user.pk,
            billing_email=user.email,
            full_name=user.full_name,
        )


def delete_customers(apps, schema_editor):
    # Allow reverting this migration when in DEBUG mode only
    if not settings.DEBUG:
        return
    Customer = apps.get_model('looper', 'Customer')

    Customer.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_user_date_deletion_requested'),
        ('subscriptions', '0003_add_product_and_plans'),
    ]

    operations = [
        migrations.RunPython(create_customers, reverse_code=delete_customers),
    ]
