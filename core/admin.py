from django.contrib import admin
from django.contrib import messages
from django.db import transaction

from .models import CartItem, Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "compare_at_price", "stock")
    list_filter = ("category", "size", "color")
    list_editable = ("stock",)
    search_fields = ("name", "category")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "added_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ("product_name", "unit_price", "quantity")
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("public_id", "customer_name", "phone", "total", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("=public_id", "customer_name", "phone")
    readonly_fields = (
        "public_id",
        "customer_name",
        "phone",
        "address",
        "total",
        "status",
        "created_at",
    )
    fields = readonly_fields
    inlines = (OrderItemInline,)
    actions = (
        "confirm_orders",
        "mark_orders_shipped",
        "mark_orders_delivered",
        "cancel_orders",
    )

    @admin.action(description="Confirm pending orders")
    def confirm_orders(self, request, queryset):
        self._transition_orders(
            request,
            queryset,
            Order.Status.PENDING,
            Order.Status.CONFIRMED,
        )

    @admin.action(description="Mark confirmed orders as shipped")
    def mark_orders_shipped(self, request, queryset):
        self._transition_orders(
            request,
            queryset,
            Order.Status.CONFIRMED,
            Order.Status.SHIPPED,
        )

    @admin.action(description="Mark shipped orders as delivered")
    def mark_orders_delivered(self, request, queryset):
        self._transition_orders(
            request,
            queryset,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
        )

    @admin.action(description="Cancel open orders and return stock")
    def cancel_orders(self, request, queryset):
        with transaction.atomic():
            orders = list(queryset.select_for_update())
            for order in orders:
                if order.status in (
                    Order.Status.PENDING,
                    Order.Status.CONFIRMED,
                    Order.Status.SHIPPED,
                ):
                    order.transition_to(Order.Status.CANCELLED)
        self.message_user(
            request,
            "Eligible orders cancelled and reserved stock returned.",
            messages.SUCCESS,
        )

    def _transition_orders(self, request, queryset, current_status, new_status):
        orders = queryset.filter(status=current_status)
        with transaction.atomic():
            for order in orders.select_for_update():
                order.transition_to(new_status)
        self.message_user(
            request,
            f"Eligible orders marked as {new_status}.",
            messages.SUCCESS,
        )