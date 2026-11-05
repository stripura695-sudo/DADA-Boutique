import uuid

from django.core.validators import MinValueValidator
from django.db import transaction
from django.db.models import F
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=80,
        default="Jackets",
        help_text="For example: T-Shirts, Shirts, or Jackets.",
    )
    size = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=60, blank=True)
    fit = models.CharField(max_length=60, blank=True)
    fabrication = models.CharField(max_length=80, blank=True)
    embellishments = models.CharField(max_length=80, blank=True)
    sleeve_length = models.CharField(max_length=60, blank=True)
    item_segment = models.CharField(max_length=60, blank=True)
    price = models.IntegerField(validators=[MinValueValidator(0)])
    compare_at_price = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Optional original price; set above the current price to show a sale.",
    )
    stock = models.PositiveIntegerField(
        default=0,
        help_text="Set the available quantity before publishing this product.",
    )
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True)


    def __str__(self):
        return self.name

    @property
    def discount_percentage(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return round(
                (self.compare_at_price - self.price) * 100 / self.compare_at_price
            )
        return 0

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    total = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.public_id} ({self.get_status_display()})"

    def transition_to(self, new_status):
        transitions = {
            self.Status.PENDING: {self.Status.CONFIRMED, self.Status.CANCELLED},
            self.Status.CONFIRMED: {self.Status.SHIPPED, self.Status.CANCELLED},
            self.Status.SHIPPED: {self.Status.DELIVERED, self.Status.CANCELLED},
            self.Status.DELIVERED: set(),
            self.Status.CANCELLED: set(),
        }
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if new_status not in transitions[order.status]:
                raise ValueError(
                    f"Cannot change order status from {order.status} to {new_status}."
                )
            if new_status == self.Status.CANCELLED:
                for item in order.items.filter(product__isnull=False):
                    Product.objects.filter(pk=item.product_id).update(
                        stock=F("stock") + item.quantity
                    )
            order.status = new_status
            order.save(update_fields=["status"])
        self.status = new_status


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name="order_items",
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=100)
    unit_price = models.PositiveBigIntegerField()
    quantity = models.PositiveIntegerField()

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"