from urllib.parse import parse_qs, urlparse

from django.contrib.staticfiles.finders import find
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Order, OrderItem, Product


class ShopWorkflowTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Winter Jacket",
            price=2500,
            stock=20,
            description="Warm jacket",
        )

    def add_product_to_cart(self, quantity=1):
        url = reverse("core:add_to_cart", args=[self.product.pk])
        for _ in range(quantity):
            self.client.post(url)

    def checkout_data(self):
        return {
            "name": "Test Customer",
            "phone": "01700000000",
            "address": "Test Street, Dhaka",
        }

    def test_homepage_search_filters_products(self):
        Product.objects.create(name="Rain Coat", price=1800, stock=5)

        response = self.client.get(reverse("core:home"), {"search": "winter"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["products"].values_list("name", flat=True)),
            ["Winter Jacket"],
        )

    def test_homepage_shows_featured_product_and_animation_assets(self):
        Product.objects.create(name="Rain Coat", price=1800, stock=5)

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ঠান্ডায় থাকুন")
        self.assertContains(response, "Winter Jacket")
        self.assertContains(response, "core/shop.css")
        self.assertContains(response, "core/shop.js")
        self.assertContains(response, "swiper-wrapper")
        self.assertContains(response, "hero-slider-next")
        self.assertContains(response, "autoplay")

    def test_design_assets_are_available_during_local_development(self):
        css_path = find("core/shop.css")
        js_path = find("core/shop.js")

        self.assertIsNotNone(css_path)
        self.assertIsNotNone(js_path)
        with open(css_path, encoding="utf-8") as css_file:
            self.assertIn("prefers-reduced-motion", css_file.read())
        with open(js_path, encoding="utf-8") as js_file:
            self.assertIn("IntersectionObserver", js_file.read())

    def test_contact_and_delivery_policy_pages_render(self):
        contact_response = self.client.get(reverse("core:contact"))
        policy_response = self.client.get(reverse("core:delivery_policy"))
        about_response = self.client.get(reverse("core:about"))
        privacy_response = self.client.get(reverse("core:privacy_policy"))

        self.assertEqual(contact_response.status_code, 200)
        self.assertContains(contact_response, "WhatsApp")
        self.assertEqual(policy_response.status_code, 200)
        self.assertContains(policy_response, "ডেলিভারি ও রিটার্ন")
        self.assertContains(policy_response, 'id="returns"')
        self.assertEqual(about_response.status_code, 200)
        self.assertEqual(privacy_response.status_code, 200)
        self.assertContains(privacy_response, "ফোন নম্বর")

    def test_footer_shows_working_shop_links_and_real_payment_method(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, reverse("core:about"))
        self.assertContains(response, reverse("core:contact"))
        self.assertContains(response, reverse("core:privacy_policy"))
        self.assertContains(response, "Dada Boys’ Wear")
        self.assertContains(response, "core/images/dada-boys-wear-logo.png")
        self.assertContains(response, "8801867574616")
        self.assertContains(response, "CASH ON DELIVERY")
        self.assertContains(response, "অনলাইন কার্ড বা mobile banking payment এই মুহূর্তে নেই")

    def test_mega_menu_lists_real_products_and_store_pages(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, 'aria-label="পণ্য ও দোকানের নেভিগেশন"')
        self.assertContains(response, "ছেলেদের কালেকশন")
        self.assertContains(response, "Winter Jacket")
        self.assertContains(response, reverse("core:product_detail", args=[self.product.pk]))
        self.assertContains(response, reverse("core:delivery_policy"))
        self.assertContains(response, reverse("core:shop_catalog"))
        self.assertContains(response, "core/menu.js")

    def test_shop_catalog_filters_by_category_size_and_price(self):
        self.product.size = "M"
        self.product.save(update_fields=["size"])
        Product.objects.create(
            name="Kids' Shirt",
            category="Shirts",
            size="L",
            price=1200,
            stock=4,
        )

        response = self.client.get(
            reverse("core:shop_catalog"),
            {
                "category": "Jackets",
                "size": "M",
                "min_price": "2000",
                "max_price": "3000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["products"].values_list("name", flat=True)),
            ["Winter Jacket"],
        )
        self.assertContains(response, "ALL COLLECTION")
        self.assertContains(response, "Price Range")

    def test_shop_catalog_displays_sale_price_and_filters_sale_products(self):
        sale_product = Product.objects.create(
            name="Sale Shirt",
            category="Shirts",
            price=800,
            compare_at_price=1000,
            stock=3,
        )

        response = self.client.get(
            reverse("core:shop_catalog"),
            {"sale": "1", "category": "Shirts"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["products"].values_list("pk", flat=True)),
            [sale_product.pk],
        )
        self.assertContains(response, "20% OFF")
        self.assertContains(response, "৳ 1000")

    def test_shop_catalog_reports_invalid_price_range_without_showing_unfiltered_items(self):
        response = self.client.get(
            reverse("core:shop_catalog"),
            {"min_price": "3000", "max_price": "1000"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 0)
        self.assertContains(response, "দামের সীমা সঠিকভাবে লিখুন")

    def test_product_detail_handles_missing_image(self):
        response = self.client.get(
            reverse("core:product_detail", args=[self.product.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Winter Jacket")

    def test_product_detail_shows_apparel_specs_and_sale_price(self):
        self.product.size = "M"
        self.product.color = "Navy"
        self.product.compare_at_price = 3000
        self.product.save(update_fields=["size", "color", "compare_at_price"])

        response = self.client.get(
            reverse("core:product_detail", args=[self.product.pk])
        )

        self.assertContains(response, "Navy")
        self.assertContains(response, "M")
        self.assertContains(response, "৳ 3000")
        self.assertContains(response, "17% ছাড়")

    def test_cart_is_session_specific_and_quantity_can_be_updated(self):
        response = self.client.post(
            reverse("core:add_to_cart", args=[self.product.pk])
        )

        self.assertRedirects(response, reverse("core:cart_view"))
        self.assertEqual(
            len(self.client.get(reverse("core:cart_view")).context["cart_items"]),
            1,
        )

        other_client = self.client_class()
        other_cart = other_client.get(reverse("core:cart_view"))
        self.assertEqual(len(other_cart.context["cart_items"]), 0)

        response = self.client.post(
            reverse("core:update_cart_quantity", args=[self.product.pk]),
            {"quantity": 3},
        )

        self.assertRedirects(response, reverse("core:cart_view"))
        self.assertContains(self.client.get(reverse("core:cart_view")), "7500")

    def test_cart_changes_require_post(self):
        response = self.client.get(
            reverse("core:add_to_cart", args=[self.product.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_cart_item_can_be_removed(self):
        self.add_product_to_cart()

        response = self.client.post(
            reverse("core:remove_from_cart", args=[self.product.pk])
        )

        self.assertRedirects(response, reverse("core:cart_view"))
        self.assertEqual(
            len(self.client.get(reverse("core:cart_view")).context["cart_items"]),
            0,
        )

    def test_checkout_creates_order_snapshots_and_reserves_stock(self):
        self.add_product_to_cart(quantity=2)

        response = self.client.post(
            reverse("core:checkout"),
            self.checkout_data(),
        )

        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse("core:order_tracking", args=[order.public_id]),
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 18)
        self.assertEqual(order.total, 5000)
        self.assertEqual(order.status, Order.Status.PENDING)
        item = OrderItem.objects.get(order=order)
        self.assertEqual(item.product_name, "Winter Jacket")
        self.assertEqual(item.unit_price, 2500)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(self.client.session["cart"], {})

    def test_tracking_page_shows_status_without_customer_contact_details(self):
        self.add_product_to_cart()
        response = self.client.post(
            reverse("core:checkout"),
            self.checkout_data(),
        )
        order = Order.objects.get()

        tracking = self.client.get(response.url)

        self.assertEqual(tracking.status_code, 200)
        self.assertContains(tracking, str(order.public_id))
        self.assertContains(tracking, "Winter Jacket")
        self.assertNotContains(tracking, "01700000000")
        self.assertNotContains(tracking, "Test Street, Dhaka")
        message = parse_qs(urlparse(tracking.context["whatsapp_url"]).query)["text"][0]
        self.assertIn(str(order.public_id), message)
        self.assertIn("Winter Jacket x 1 = ৳2500", message)
        self.assertIn("সর্বমোট: ৳2500", message)

    def test_cancelling_order_restores_reserved_stock(self):
        self.add_product_to_cart(quantity=2)
        self.client.post(reverse("core:checkout"), self.checkout_data())
        order = Order.objects.get()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 18)

        order.transition_to(Order.Status.CANCELLED)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 20)
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_invalid_order_status_transition_is_rejected(self):
        self.add_product_to_cart()
        self.client.post(reverse("core:checkout"), self.checkout_data())
        order = Order.objects.get()

        with self.assertRaises(ValueError):
            order.transition_to(Order.Status.DELIVERED)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_checkout_rejects_order_if_stock_changed(self):
        self.add_product_to_cart()
        Product.objects.filter(pk=self.product.pk).update(stock=0)

        response = self.client.post(
            reverse("core:checkout"),
            self.checkout_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "স্টক পরিবর্তিত হয়েছে")
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.client.session["cart"], {str(self.product.pk): 1})

    def test_checkout_rejects_negative_product_price(self):
        self.add_product_to_cart()
        Product.objects.filter(pk=self.product.pk).update(price=-1)

        response = self.client.post(
            reverse("core:checkout"),
            self.checkout_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "পণ্যের দাম সঠিক নয়")
        self.assertFalse(Order.objects.exists())

    def test_add_to_cart_rejects_out_of_stock_product(self):
        Product.objects.filter(pk=self.product.pk).update(stock=0)

        response = self.client.post(
            reverse("core:add_to_cart", args=[self.product.pk])
        )

        self.assertRedirects(response, reverse("core:cart_view"))
        self.assertEqual(
            len(self.client.get(reverse("core:cart_view")).context["cart_items"]),
            0,
        )

    def test_checkout_rejects_empty_cart(self):
        response = self.client.get(reverse("core:checkout"))

        self.assertRedirects(response, reverse("core:cart_view"))

    def test_invalid_quantity_does_not_update_cart(self):
        self.add_product_to_cart()

        response = self.client.post(
            reverse("core:update_cart_quantity", args=[self.product.pk]),
            {"quantity": 0},
        )

        self.assertRedirects(response, reverse("core:cart_view"))
        self.assertContains(self.client.get(reverse("core:cart_view")), "2500")

    def test_admin_product_and_order_pages_render(self):
        admin_user = get_user_model().objects.create_superuser(
            username="shop-admin",
            email="admin@example.com",
            password="test-only-password",
        )
        self.client.force_login(admin_user)

        product_page = self.client.get(
            reverse("admin:core_product_changelist")
        )
        order_page = self.client.get(reverse("admin:core_order_changelist"))

        self.assertEqual(product_page.status_code, 200)
        self.assertContains(product_page, "Winter Jacket")
        self.assertEqual(order_page.status_code, 200)
