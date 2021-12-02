from decimal import Decimal
from io import BytesIO
from unittest.mock import patch, Mock

from PyPDF2 import PdfFileReader
from django.test.testcases import TestCase
from django.urls import reverse

from looper.tests.factories import PaymentMethodFactory, OrderFactory
import looper.taxes

from common.tests.factories.subscriptions import (
    create_customer_with_billing_address,
)
from common.tests.factories.users import UserFactory

expected_text_tmpl = '''
Invoice
Blender Studio B.V.
Buikslotermeerplein 161
1025 ET Amsterdam, the Netherlands
Tax number NL861711932B01
Billing Address
E-mail: {order.email}{expected_vatin}
Invoice Number:
{order.number}
Invoice Date:
{expected_date}
Payment method:
Product
Quantity
Price
Blender Studio Subscription
Subscription #: {order.subscription_id}
Renewal type: Automatic
Renewal period: Monthly
1
{expected_currency_symbol} {expected_price}{expected_additional_note}
Subtotal
{expected_currency_symbol} {expected_subtotal}{expected_vat}
Total
{expected_currency_symbol} {expected_total}
'''


@patch('looper.admin_log.attach_log_entry', Mock(return_value=None))
class TestReceiptPDFView(TestCase):
    maxDiff = None

    @classmethod
    @patch('looper.admin_log.attach_log_entry', Mock(return_value=None))
    def setUpClass(cls):
        super().setUpClass()

        user = create_customer_with_billing_address(email='mail1@example.com')
        cls.payment_method = PaymentMethodFactory(user=user)
        cls.paid_order = OrderFactory(
            user=user,
            price=990,
            status='paid',
            tax_country='NL',
            payment_method=cls.payment_method,
            subscription__payment_method=cls.payment_method,
            subscription__user=user,
            subscription__plan__product__name='Blender Studio Subscription',
        )

    def _extract_text_from_pdf(self, response):
        pdf = PdfFileReader(BytesIO(response.content))
        self.assertEqual(1, pdf.getNumPages())
        pdf_page = pdf.getPage(0)
        return pdf_page.extractText()

    def test_get_pdf_unpaid_order_not_found(self):
        unpaid_order = OrderFactory(
            user=self.payment_method.user,
            price=990,
            tax_country='NL',
            payment_method=self.payment_method,
            subscription__payment_method=self.payment_method,
            subscription__user=self.payment_method.user,
            subscription__plan_id=1,
        )
        self.client.force_login(unpaid_order.user)
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': unpaid_order.pk})
        response = self.client.get(url)

        self.assertEqual(404, response.status_code)

    def test_get_pdf_anonymous_redirects_to_login(self):
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': self.paid_order.pk})
        response = self.client.get(url)

        self.assertEqual(302, response.status_code)
        self.assertEqual(f'/oauth/login?next={url}', response['Location'])

    def test_get_pdf_someone_elses_order_not_found(self):
        another_user = UserFactory()

        self.client.force_login(another_user)
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': self.paid_order.pk})
        response = self.client.get(url)

        self.assertEqual(404, response.status_code)

    def test_get_pdf_has_logo(self):
        self.client.force_login(self.paid_order.user)
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': self.paid_order.pk})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        self.assertEqual(b'%PDF-', response.content[:5])

        # Check that the image is there.
        self.assertIn(b'/Subtype /Image', response.content)
        self.assertIn(b'/Height 103', response.content)
        self.assertIn(b'/Width 400', response.content)

        self._extract_text_from_pdf(response)

    def test_get_pdf_total_vat_charged(self):
        taxable = looper.taxes.Taxable(
            looper.money.Money('EUR', 1490),
            tax_type=looper.taxes.TaxType.VAT_CHARGE,
            tax_rate=Decimal(19),
        )
        order = OrderFactory(
            price=taxable.price,
            status='paid',
            tax=taxable.tax,
            tax_country='DE',
            tax_type=taxable.tax_type.value,
            tax_rate=taxable.tax_rate,
            email='billing@example.com',
            subscription__plan_id=1,
        )
        self.client.force_login(order.user)
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': order.pk})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)

        pdf_text = self._extract_text_from_pdf(response)
        self.assertEqual(
            pdf_text,
            expected_text_tmpl.format(
                order=order,
                expected_vatin='',
                expected_date=order.paid_at.strftime("%b. %-d, %Y"),
                expected_currency_symbol='•',
                expected_price='12.52',
                expected_additional_note='',
                expected_subtotal='12.52 (ex. VAT)',
                expected_vat='\nVAT (19%)\n• 2.38',
                expected_total='14.90',
            ),
        )

    def test_get_pdf_total_vat_reverse_charged(self):
        taxable = looper.taxes.Taxable(
            looper.money.Money('EUR', 1490),
            tax_type=looper.taxes.TaxType.VAT_REVERSE_CHARGE,
            tax_rate=Decimal(19),
        )
        order = OrderFactory(
            price=taxable.price,
            status='paid',
            tax=taxable.tax,
            tax_country='DE',
            tax_type=taxable.tax_type.value,
            tax_rate=taxable.tax_rate,
            vat_number='DE123456789',
            email='billing@example.com',
            subscription__plan_id=1,
        )
        self.client.force_login(order.user)
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': order.pk})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)

        pdf_text = self._extract_text_from_pdf(response)
        self.assertEqual(
            pdf_text,
            expected_text_tmpl.format(
                order=order,
                expected_vatin='\nVATIN: DE123456789',
                expected_date=order.paid_at.strftime("%b. %-d, %Y"),
                # FIXME(anna): PyPDF2's extractText() doesn't extract EUR sign for some reason
                expected_currency_symbol='•',
                expected_price='12.52',
                expected_subtotal='12.52 (ex. VAT)',
                expected_additional_note=(
                    '\nUnder the regulations of the EU we do not charge VAT on services provided to VAT-registered'
                    '\nbusinesses in other member countries. According to the reverse-charge regulations on tax'
                    '\nliability transfers to the recipient of services.'
                ),
                expected_vat='',
                expected_total='12.52',
            ),
        )

    def test_get_pdf_total_vat_charged_nl(self):
        taxable = looper.taxes.Taxable(
            looper.money.Money('EUR', 1490),
            tax_type=looper.taxes.TaxType.VAT_CHARGE,
            tax_rate=Decimal(21),
        )
        order = OrderFactory(
            price=taxable.price,
            status='paid',
            tax=taxable.tax,
            tax_country='NL',
            tax_type=taxable.tax_type.value,
            tax_rate=taxable.tax_rate,
            vat_number='NL123456789',
            email='billing@example.com',
            subscription__plan_id=1,
        )
        self.client.force_login(order.user)
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': order.pk})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)

        pdf_text = self._extract_text_from_pdf(response)
        self.assertEqual(
            pdf_text,
            expected_text_tmpl.format(
                order=order,
                expected_vatin='\nVATIN: NL123456789',
                expected_date=order.paid_at.strftime("%b. %-d, %Y"),
                # FIXME(anna): PyPDF2's extractText() doesn't extract EUR sign for some reason
                expected_currency_symbol='•',
                expected_price='12.31',
                expected_subtotal='12.31 (ex. VAT)',
                expected_additional_note='',
                expected_vat='\nVAT (21%)\n• 2.59',
                expected_total='14.90',
            ),
        )

    def test_get_pdf_total_no_vat(self):
        order = OrderFactory(
            price=1000,
            currency='USD',
            status='paid',
            tax_country='US',
            email='billing@example.com',
            subscription__plan_id=1,
        )
        self.client.force_login(order.user)
        url = reverse('subscriptions:receipt-pdf', kwargs={'order_id': order.pk})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)

        pdf_text = self._extract_text_from_pdf(response)
        self.assertEqual(
            pdf_text,
            expected_text_tmpl.format(
                order=order,
                expected_vatin='',
                expected_date=order.paid_at.strftime("%b. %-d, %Y"),
                expected_currency_symbol='$',
                expected_price='10',
                expected_additional_note='',
                expected_subtotal='10',
                expected_vat='',
                expected_total='10',
            ),
        )
