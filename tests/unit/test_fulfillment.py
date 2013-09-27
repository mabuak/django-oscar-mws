import mock
import httpretty

from django.test import TestCase
from django.db.models import get_model

from oscar_testsupport.factories import create_order, create_product

from oscar_mws.test import mixins, factories
from oscar_mws.fulfillment.creator import FulfillmentOrderCreator

Country = get_model('address', 'Country')
Basket = get_model('basket', 'Basket')
ShippingAddress = get_model('order', 'ShippingAddress')


class TestFulfillmentShipmentCreator(TestCase):
    fixtures = ['countries']

    def setUp(self):
        super(TestFulfillmentShipmentCreator, self).setUp()
        self.merchant = factories.MerchantAccountFactory()
        self.creator = FulfillmentOrderCreator(merchant=self.merchant)
        self.address = ShippingAddress.objects.create(
            first_name='test',
            last_name='man',
            line1="123 Imanginary Ave",
            line4="Funky Town",
            postcode="56789",
            country=Country.objects.all()[0],
        )

    def test_creates_shipments_for_single_address(self):
        order = create_order(shipping_address=self.address)

        self.creator.create_fulfillment_order(order)

    def test_creates_shipments_for_multiple_addresses(self):
        basket = Basket.open.create()
        basket.add_product(create_product())
        basket.add_product(create_product())

        second_address = ShippingAddress.objects.create(
            first_name="test man's friend",
            line1="1 Random Way",
            line4="Spooky Village",
            postcode="56789",
            country=Country.objects.all()[0],
        )

        order = create_order(basket=basket, shipping_address=self.address)
        order.get_fulfillment_addresses = mock.Mock(
            return_value=[self.address, second_address]
        )
        order.get_lines_for_address = mock.Mock()
        order.get_lines_for_address.side_effect = [
            order.lines.all()[0:1],
            order.lines.all()[1:]
        ]

        self.creator.create_fulfillment_order(order)


class TestUpdatingFulfillmentOrders(mixins.DataLoaderMixin, TestCase):

    @httpretty.activate
    def test_updates_a_single_order_status(self):
        httpretty.register_uri(
            httpretty.POST,
            'https://mws.amazonservices.com/',
            responses=[httpretty.Response(
                self.load_data('get_fulfillment_order_response.xml'),
            )],
        )
