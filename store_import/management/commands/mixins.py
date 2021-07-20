"""Handles inserting Store's data into Studio's database."""
from typing import List, Dict, Any
import logging
import time

from django.contrib.admin.models import LogEntry
from django.db import transaction

from looper.models import (
    Address,
    Customer,
    GatewayCustomerId,
    Order,
    PaymentMethod,
    Subscription,
    Transaction,
)

logger = logging.getLogger('store_import')


class _UpsertMixin:
    def _reset(self):
        self.customers_to_upsert: List[Customer] = []
        self.gateway_customers_to_upsert: List[GatewayCustomerId] = []
        self.addresses_to_upsert: List[Address] = []
        self.payment_methods_to_upsert: List[PaymentMethod] = []
        self.subscriptions_to_upsert: List[Subscription] = []
        self.orders_to_upsert: List[Order] = []
        self.transactions_to_upsert: List[Transaction] = []
        # self.log_entries_to_upsert: List[LogEntry] = []
        self.log_entries_to_upsert: List[Dict[str, Any]] = []

    def _get_fields_for_update(self, model):
        fields = []
        for f in model._meta.get_fields():
            if not f.concrete or f.many_to_many:
                continue
            if f.primary_key:
                continue
            fields.append(f.name)
        return fields

    def _separate_new_existing(self, model, objects, pk_field='id', **filters):
        obj_ids = set(getattr(s, pk_field) for s in objects)
        # filters = {f'{pk_field}__in': obj_ids}
        if not filters:
            filters = {f'{pk_field}__in': obj_ids}
        existing_ids = set(_[pk_field] for _ in model.objects.filter(**filters).values(pk_field))
        new_objects = [s for s in objects if getattr(s, pk_field) not in existing_ids]
        existing_objects = [s for s in objects if getattr(s, pk_field) in existing_ids]
        logger.info(
            '%s new, %s existing %s to upsert',
            len(new_objects),
            len(existing_objects),
            model.__name__,
        )
        return new_objects, existing_objects

    def _set_payment_method_fields(self, payment_methods: List[PaymentMethod]) -> None:
        # Set payment gateways for all payment methods
        for pm in payment_methods:
            # FIXME(anna): make this an option or remove
            # pm.token = str(pm.token) + 'test'
            if pm.method_type in ('cc', 'pa'):
                pm.gateway = self.gateways['braintree']
            elif pm.method_type == 'ba':
                pm.gateway = self.gateways['bank']
                pm.recognisable_name = 'Bank Transfer'
            else:
                raise Exception(f'Unknown payment method: {pm.method_type} {pm.token}')

    def _upsert(self):
        # Save all the subscription data gathered so far
        if (
            self.total_count > self.BATCH_SIZE
            and len(self.subscriptions_to_upsert) < self.BATCH_SIZE
        ):
            return
        _start_t = time.time()
        with transaction.atomic():
            # Order of insertion is important because of the FKs
            self._upsert_customers()
            self._upsert_addresses()
            self._upsert_payment_methods()
            self._upsert_subscriptions()
            self._upsert_orders()
            self._upsert_transactions()
            # self._upsert_log_entries()
        self._reset()
        logger.info('Took %s to upsert', time.time() - _start_t)

    def _upsert_customers(self) -> None:
        for customer in self.customers_to_upsert:
            customer.save()

        new_gateway_customers = {}
        existing_gateway_customers = []
        for gwc in self.gateway_customers_to_upsert:
            assert gwc.user_id
            assert gwc.gateway_id
            assert gwc.gateway_customer_id
            if GatewayCustomerId.objects.filter(
                user_id=gwc.user_id,
                gateway_id=gwc.gateway_id,
                gateway_customer_id=gwc.gateway_customer_id,
            ).first():
                existing_gateway_customers.append(gwc)
            else:
                key = f'{gwc.user_id}{gwc.gateway_id}{gwc.gateway_customer_id}'
                if key not in new_gateway_customers:
                    new_gateway_customers[key] = gwc
        logger.info(
            '%s new, %s existing GatewayCustomerId to upsert',
            len(new_gateway_customers),
            len(existing_gateway_customers),
        )
        GatewayCustomerId.objects.bulk_create(new_gateway_customers.values())

    def _upsert_addresses(self) -> None:
        new_addresses, existing_addresses = self._separate_new_existing(
            # There's always only one address per user
            Address,
            self.addresses_to_upsert,
            pk_field='user_id',
        )
        Address.objects.bulk_create(new_addresses)
        Address.objects.bulk_update(existing_addresses, fields=self._get_fields_for_update(Address))

    def _upsert_subscriptions(self) -> None:
        for s in self.subscriptions_to_upsert:
            if s.payment_method:
                s.payment_method_id = s.payment_method.pk

        new_subscriptions, existing_subscriptions = self._separate_new_existing(
            Subscription, self.subscriptions_to_upsert
        )
        Subscription.objects.bulk_create(new_subscriptions, batch_size=self.BATCH_SIZE)
        Subscription.objects.bulk_update(
            existing_subscriptions,
            fields=self._get_fields_for_update(Subscription),
        )

    def _upsert_payment_methods(self) -> None:
        # There might have been duplicates in the previous batches, check for them:
        _new_payment_methods = {}
        for pm in self.payment_methods_to_upsert:
            existing_pm = PaymentMethod.objects.filter(
                user_id=pm.user_id, gateway_id=pm.gateway_id, token=pm.token
            ).first()
            if existing_pm:
                logger.debug('Found an existing payment method %s', existing_pm)
                pm.pk = existing_pm.pk
            else:
                key = f'{pm.user_id}{pm.gateway_id}{pm.token}'
                _new_payment_methods[key] = pm

        PaymentMethod.objects.bulk_create(_new_payment_methods.values())

        # Set IDs on all of the payment methods, in case there were duplicates in this batch
        for pm in self.payment_methods_to_upsert:
            key = f'{pm.user_id}{pm.gateway_id}{pm.token}'
            if not pm.pk and key in _new_payment_methods:
                pm.pk = _new_payment_methods[key].pk
                logger.debug('Using ID of a found duplicate payment method %s', pm)

    def _upsert_orders(self) -> None:
        for o in self.orders_to_upsert:
            # assert o.payment_method
            if o.payment_method:
                o.payment_method_id = o.payment_method.pk

        new_orders, existing_orders = self._separate_new_existing(Order, self.orders_to_upsert)
        Order.objects.bulk_create(new_orders, batch_size=self.BATCH_SIZE)
        Order.objects.bulk_update(
            existing_orders, fields=self._get_fields_for_update(Order), batch_size=self.BATCH_SIZE
        )

    def _upsert_transactions(self) -> None:
        for t in self.transactions_to_upsert:
            assert t.payment_method.pk, (
                f'Missing ID for transaction payment method {t.payment_method}'
                f'of {t.order.subscription.pk}'
            )
            t.payment_method_id = t.payment_method.pk

        new_transactions = {}
        existing_transactions = {}
        for t in self.transactions_to_upsert:
            assert t.user_id
            assert t.order_id
            key = f'{t.order_id}{t.transaction_id}'
            existing_t = Transaction.objects.filter(
                order_id=t.order_id,
                transaction_id=t.transaction_id,
            ).first()
            if existing_t:
                t.pk = existing_t.pk
                if key not in existing_transactions:
                    existing_transactions[key] = t
            else:
                if key not in new_transactions:
                    new_transactions[key] = t
        logger.info(
            '%s new, %s existing Transactions to upsert',
            len(new_transactions),
            len(existing_transactions),
        )
        Transaction.objects.bulk_create(new_transactions.values(), batch_size=self.BATCH_SIZE)
        Transaction.objects.bulk_update(
            existing_transactions.values(),
            fields=self._get_fields_for_update(Transaction),
            batch_size=self.BATCH_SIZE,
        )


class _UpsertLogEntriesMixin:
    def _reset(self):
        # self.log_entries_to_upsert: List[LogEntry] = []
        self.log_entries_to_upsert: List[Dict[str, Any]] = []

    def _get_fields_for_update(self, model):
        fields = []
        for f in model._meta.get_fields():
            if not f.concrete or f.many_to_many:
                continue
            if f.primary_key:
                continue
            fields.append(f.name)
        return fields

    def _separate_new_existing(self, model, objects, pk_field='id', **filters):
        obj_ids = set(getattr(s, pk_field) for s in objects)
        # filters = {f'{pk_field}__in': obj_ids}
        if not filters:
            filters = {f'{pk_field}__in': obj_ids}
        existing_ids = set(_[pk_field] for _ in model.objects.filter(**filters).values(pk_field))
        new_objects = [s for s in objects if getattr(s, pk_field) not in existing_ids]
        existing_objects = [s for s in objects if getattr(s, pk_field) in existing_ids]
        logger.info(
            '%s new, %s existing %s to upsert',
            len(new_objects),
            len(existing_objects),
            model.__name__,
        )
        return new_objects, existing_objects

    def _upsert(self):
        # Save all the subscription data gathered so far
        if self.total_count > self.BATCH_SIZE and len(self.log_entries_to_upsert) < self.BATCH_SIZE:
            return
        _start_t = time.time()
        with transaction.atomic():
            self._upsert_log_entries()
        self._reset()
        logger.info('Took %s to upsert', time.time() - _start_t)

    def _delete_existing_log_entries(self, entry_data):
        LogEntry.objects.filter(
            object_id=entry_data['object_id'], content_type_id=entry_data['content_type_id']
        ).delete()

    def _upsert_log_entries(self) -> None:
        LogEntry.objects.bulk_create([LogEntry(**_) for _ in self.log_entries_to_upsert])
