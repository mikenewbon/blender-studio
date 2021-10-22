from django.conf import settings
from django.db import migrations

description_automatic = 'This subscription is renewed automatically. You can stop or cancel a subscription any time.'
description_manual = 'This subscription is renewed manually. You can leave it on-hold, or renew it when convenient.'

plan_variations = [
    # Method, int unit, int length, currency, price, is default for currency
    (
        'Automatic renewal', description_automatic, 'automatic',
        ('month', 1, 'USD', 1150, True),
        ('month', 1, 'EUR', 990, True),
        ('month', 3, 'USD', 3200, False),
        ('month', 3, 'EUR', 2850, False),
        ('month', 6, 'USD', 6150, False),
        ('month', 6, 'EUR', 5550, False),
        ('year', 1, 'USD', 11900, False),
        ('year', 1, 'EUR', 10900, False),
    ),

    (
        'Manual renewal', description_manual, 'manual',
        ('month', 1, 'USD', 1700, False),
        ('month', 1, 'EUR', 1490, False),
        ('month', 3, 'USD', 3700, False),
        ('month', 3, 'EUR', 3200, False),
        ('year', 1, 'USD', 12700, False),
        ('year', 1, 'EUR', 11900, False),
    ),
]


def add_product_and_plans(apps, schema_editor):
    from looper.taxes import ProductType
    Product = apps.get_model('looper', 'Product')
    Plan = apps.get_model('looper', 'Plan')
    PlanVariation = apps.get_model('looper', 'PlanVariation')
    product, _ = Product.objects.get_or_create(
        name='Blender Studio Subscription',
        type=ProductType.ELECTRONIC_SERVICE.value
    )
    for params in plan_variations:
        name, description, method = params[:3]
        plan, _ = Plan.objects.get_or_create(
            product=product,
            name=name,
            description=description,
        )
        for (
            interval_unit, interval_length, currency, price, is_default_for_currency
        ) in params[3:]:
            variation, _ = PlanVariation.objects.get_or_create(
                plan=plan,
                currency=currency,
                price=price,
                collection_method=method,
                interval_unit=interval_unit,
                interval_length=interval_length,
                is_default_for_currency=is_default_for_currency,
            )


def remove_product_and_plans(apps, schema_editor):
    # Allow reverting this migration when in DEBUG mode only
    if not settings.DEBUG:
        return
    Product = apps.get_model('looper', 'Product')
    Plan = apps.get_model('looper', 'Plan')
    PlanVariation = apps.get_model('looper', 'PlanVariation')

    PlanVariation.objects.all().delete()
    Plan.objects.all().delete()
    Product.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0002_add_gateways'),
    ]

    operations = [
        migrations.RunPython(add_product_and_plans, reverse_code=remove_product_and_plans),
    ]
