
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Product
from .models import Order, OrderItem


class OrderModelTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer1",
            password="TestPassword123!",
        )

        self.farmer = User.objects.create_user(
            username="farmer1",
            password="TestPassword123!",
        )

        self.product = Product.objects.create(
            farmer=self.farmer,
            name="Fresh Tomatoes",
            description="Farm-fresh tomatoes",
            category="vegetables",
            price=Decimal("30.00"),
            unit="kg",
            quantity=10,
            is_available=True,
        )

        self.order = Order.objects.create(
            customer=self.customer,
            delivery_address="House 10, Warangal, Telangana",
            total_amount=Decimal("60.00"),
        )

        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal("30.00"),
        )

    def test_order_is_created_with_pending_status(self):
        self.assertEqual(self.order.status, "pending")

    def test_order_belongs_to_correct_customer(self):
        self.assertEqual(self.order.customer, self.customer)

    def test_order_item_has_correct_subtotal(self):
        subtotal = self.order_item.price * self.order_item.quantity
        self.assertEqual(subtotal, Decimal("60.00"))

    def test_product_belongs_to_correct_farmer(self):
        self.assertEqual(self.product.farmer, self.farmer)

    def test_order_contains_its_items(self):
        self.assertEqual(self.order.items.count(), 1)
        self.assertEqual(
            self.order.items.first().product.name,
            "Fresh Tomatoes",
        )


class CheckoutTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="checkout_customer",
            password="TestPassword123!",
        )

        self.farmer = User.objects.create_user(
            username="checkout_farmer",
            password="TestPassword123!",
        )

        self.product = Product.objects.create(
            farmer=self.farmer,
            name="Fresh Tomatoes",
            description="Farm-fresh tomatoes",
            category="vegetables",
            price=Decimal("30.00"),
            unit="kg",
            quantity=10,
            is_available=True,
        )

        self.client.force_login(self.customer)

        session = self.client.session
        session["cart"] = {str(self.product.pk): 2}
        session.save()

    def test_checkout_page_loads(self):
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)

    def test_checkout_creates_order_and_deducts_stock(self):
        response = self.client.post(
            reverse("checkout"),
            {
                "delivery_address": "House 10, Warangal, Telangana",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Order.objects.filter(customer=self.customer).count(),
            1,
        )

        order = Order.objects.get(customer=self.customer)

        self.assertEqual(order.status, "pending")
        self.assertEqual(order.total_amount, Decimal("60.00"))
        self.assertEqual(order.items.count(), 1)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 8)
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_checkout_rejects_quantity_above_stock(self):
        session = self.client.session
        session["cart"] = {str(self.product.pk): 11}
        session.save()

        self.client.post(
            reverse("checkout"),
            {
                "delivery_address": "House 10, Warangal, Telangana",
            },
        )

        self.assertEqual(
            Order.objects.filter(customer=self.customer).count(),
            0,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_checkout_rejects_short_delivery_address(self):
        self.client.post(
            reverse("checkout"),
            {"delivery_address": "Short"},
        )

        self.assertEqual(
            Order.objects.filter(customer=self.customer).count(),
            0,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_checkout_rejects_unavailable_product(self):
        self.product.is_available = False
        self.product.save(update_fields=["is_available"])

        self.client.post(
            reverse("checkout"),
            {
                "delivery_address": "House 10, Warangal, Telangana",
            },
        )

        self.assertEqual(
            Order.objects.filter(customer=self.customer).count(),
            0,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_checkout_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("checkout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)


class OrderCancellationTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            username="cancel_customer",
            password="TestPassword123!",
        )

        self.other_customer = User.objects.create_user(
            username="other_customer",
            password="TestPassword123!",
        )

        self.farmer = User.objects.create_user(
            username="cancel_farmer",
            password="TestPassword123!",
        )

        # Simulate stock remaining after checkout deducted two units.
        self.product = Product.objects.create(
            farmer=self.farmer,
            name="Fresh Carrots",
            description="Fresh farm-grown carrots",
            category="vegetables",
            price=Decimal("25.00"),
            unit="kg",
            quantity=8,
            is_available=True,
        )

        self.order = Order.objects.create(
            customer=self.customer,
            delivery_address="House 10, Warangal, Telangana",
            total_amount=Decimal("50.00"),
            status="pending",
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal("25.00"),
        )

        self.cancel_url = reverse(
            "cancel_order",
            args=[self.order.pk],
        )

        self.client.force_login(self.customer)

    def test_customer_can_cancel_pending_order_and_restore_stock(self):
        response = self.client.post(self.cancel_url)

        self.assertRedirects(
            response,
            reverse("order_detail", args=[self.order.pk]),
        )

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(self.order.status, "cancelled")
        self.assertEqual(self.product.quantity, 10)
        self.assertTrue(self.product.is_available)

    def test_cancelled_order_cannot_restore_stock_twice(self):
        self.client.post(self.cancel_url)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

        # Attempt to cancel the same order again.
        self.client.post(self.cancel_url)

        self.product.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.order.status, "cancelled")
        self.assertEqual(self.product.quantity, 10)

    def test_customer_cannot_cancel_another_customers_order(self):
        self.client.force_login(self.other_customer)

        response = self.client.post(self.cancel_url)

        self.assertEqual(response.status_code, 404)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.product.quantity, 8)

    def test_only_pending_orders_can_be_cancelled(self):
        self.order.status = "confirmed"
        self.order.save(update_fields=["status"])

        response = self.client.post(self.cancel_url)

        self.assertRedirects(
            response,
            reverse("order_detail", args=[self.order.pk]),
        )

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(self.order.status, "confirmed")
        self.assertEqual(self.product.quantity, 8)

    def test_cancel_order_requires_post(self):
        response = self.client.get(self.cancel_url)

        self.assertEqual(response.status_code, 405)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.product.quantity, 8)
