from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import CheckoutForm
from .models import Order, OrderItem, Product

CART_SESSION_KEY = "cart"
MAX_CART_QUANTITY = 99


def load_cart(request):
    stored_cart = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(stored_cart, dict):
        stored_cart = {}

    valid_cart = {
        product_id: quantity
        for product_id, quantity in stored_cart.items()
        if isinstance(product_id, str)
        and product_id.isdecimal()
        and isinstance(quantity, int)
        and not isinstance(quantity, bool)
        and 1 <= quantity <= MAX_CART_QUANTITY
    }
    products = {
        str(product.pk): product
        for product in Product.objects.filter(pk__in=valid_cart)
    }
    cart = {
        product_id: quantity
        for product_id, quantity in valid_cart.items()
        if product_id in products
    }
    if cart != request.session.get(CART_SESSION_KEY, {}):
        request.session[CART_SESSION_KEY] = cart

    items = [
        {
            "product": products[product_id],
            "quantity": quantity,
            "line_total": products[product_id].price * quantity,
        }
        for product_id, quantity in cart.items()
    ]
    total_price = sum(item["line_total"] for item in items)
    return cart, items, total_price


def home(request):
    query = request.GET.get("search", "").strip()
    products = Product.objects.all()
    if query:
        products = products.filter(name__icontains=query)
    return render(
        request,
        "home.html",
        {
            "products": products,
            "featured_product": products.filter(stock__gt=0).first() or products.first(),
            "query": query,
        },
    )


def shop_catalog(request):
    filter_fields = (
        ("category", "Category"),
        ("size", "Size"),
        ("color", "Color"),
        ("fit", "Fits"),
        ("fabrication", "Fabrication"),
        ("embellishments", "Embellishments"),
        ("sleeve_length", "Sleeve Length"),
        ("item_segment", "Item Segments"),
    )
    filters = {}
    facets = []
    products = Product.objects.all()

    for field, label in filter_fields:
        selected = request.GET.get(field, "").strip()
        if selected:
            products = products.filter(**{f"{field}__iexact": selected})
        filters[field] = selected

        options = Product.objects.exclude(**{field: ""}).order_by(field).values_list(
            field, flat=True
        ).distinct()
        facet_options = []
        for value in options:
            query = request.GET.copy()
            if value == selected:
                query.pop(field, None)
            else:
                query[field] = value
            facet_options.append(
                {
                    "value": value,
                    "selected": value == selected,
                    "url": (
                        f"?{query.urlencode()}"
                        if query
                        else reverse("core:shop_catalog")
                    ),
                }
            )
        facets.append(
            {"field": field, "label": label, "options": facet_options}
        )

    sale_only = request.GET.get("sale") == "1"
    if sale_only:
        products = products.filter(compare_at_price__gt=F("price"))

    minimum_price = request.GET.get("min_price", "").strip()
    maximum_price = request.GET.get("max_price", "").strip()
    filter_error = ""
    try:
        if minimum_price:
            minimum_value = int(minimum_price)
            if minimum_value < 0:
                raise ValueError
            products = products.filter(price__gte=minimum_value)
        if maximum_price:
            maximum_value = int(maximum_price)
            if maximum_value < 0:
                raise ValueError
            products = products.filter(price__lte=maximum_value)
        if minimum_price and maximum_price and minimum_value > maximum_value:
            raise ValueError
    except ValueError:
        filter_error = "দামের সীমা সঠিকভাবে লিখুন। সর্বনিম্ন দাম সর্বোচ্চ দামের বেশি হতে পারবে না।"
        products = Product.objects.none()

    sort = request.GET.get("sort", "newest")
    ordering = {
        "newest": "-pk",
        "price_low": "price",
        "price_high": "-price",
        "name": "name",
    }
    if sort not in ordering:
        sort = "newest"

    sale_query = request.GET.copy()
    if sale_only:
        sale_query.pop("sale", None)
    else:
        sale_query["sale"] = "1"
    sort_options = [
        {"value": value, "label": label, "selected": sort == value}
        for value, label in (
            ("newest", "Newest"),
            ("price_low", "Price: Low to High"),
            ("price_high", "Price: High to Low"),
            ("name", "Name"),
        )
    ]
    preserved_params = [
        (key, value)
        for key in request.GET
        if key not in {"min_price", "max_price", "sort"}
        for value in request.GET.getlist(key)
    ]
    return render(
        request,
        "shop_catalog.html",
        {
            "products": products.order_by(ordering[sort]),
            "facets": facets,
            "filters": filters,
            "min_price": minimum_price,
            "max_price": maximum_price,
            "sale_only": sale_only,
            "sale_url": (
                f"?{sale_query.urlencode()}"
                if sale_query
                else reverse("core:shop_catalog")
            ),
            "preserved_params": preserved_params,
            "filter_error": filter_error,
            "sort_options": sort_options,
        },
    )


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "details.html", {"product": product})


def contact(request):
    return render(
        request,
        "contact.html",
        {
            "whatsapp_phone": settings.WHATSAPP_PHONE,
            "whatsapp_url": f"https://wa.me/{settings.WHATSAPP_PHONE}",
        },
    )


def delivery_policy(request):
    return render(request, "delivery_policy.html")


def about(request):
    return render(request, "about.html")


def privacy_policy(request):
    return render(request, "privacy_policy.html")


@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart, _, _ = load_cart(request)
    product_id = str(pk)
    if product.stock < 1:
        messages.error(request, "এই পণ্যটি এখন স্টকে নেই।")
        return redirect("core:cart_view")
    if cart.get(product_id, 0) >= min(product.stock, MAX_CART_QUANTITY):
        messages.error(request, "স্টকে থাকা সর্বোচ্চ পরিমাণ কার্টে যোগ হয়েছে।")
        return redirect("core:cart_view")
    cart[product_id] = cart.get(product_id, 0) + 1
    request.session[CART_SESSION_KEY] = cart
    messages.success(request, "পণ্যটি কার্টে যোগ হয়েছে।")
    return redirect("core:cart_view")


def cart_view(request):
    _, cart_items, total_price = load_cart(request)
    return render(
        request,
        "cart.html",
        {
            "cart_items": cart_items,
            "total_price": total_price,
            "cart_has_stock_issues": any(
                item["quantity"] > item["product"].stock for item in cart_items
            ),
        },
    )


@require_POST
def update_cart_quantity(request, pk):
    get_object_or_404(Product, pk=pk)
    cart, _, _ = load_cart(request)
    try:
        quantity = int(request.POST.get("quantity", ""))
    except (TypeError, ValueError):
        messages.error(request, "সঠিক পরিমাণ লিখুন।")
        return redirect("core:cart_view")

    product = get_object_or_404(Product, pk=pk)
    if product.stock < 1:
        messages.error(request, "এই পণ্যটি এখন স্টকে নেই।")
        return redirect("core:cart_view")
    if not 1 <= quantity <= min(product.stock, MAX_CART_QUANTITY):
        messages.error(
            request,
            f"পরিমাণ ১ থেকে {min(product.stock, MAX_CART_QUANTITY)}-এর মধ্যে হতে হবে।",
        )
        return redirect("core:cart_view")

    cart[str(pk)] = quantity
    request.session[CART_SESSION_KEY] = cart
    return redirect("core:cart_view")


@require_POST
def remove_from_cart(request, pk):
    cart, _, _ = load_cart(request)
    cart.pop(str(pk), None)
    request.session[CART_SESSION_KEY] = cart
    messages.success(request, "পণ্যটি কার্ট থেকে সরানো হয়েছে।")
    return redirect("core:cart_view")


def checkout(request):
    cart, cart_items, total_price = load_cart(request)
    if not cart_items:
        messages.error(request, "Checkout করার আগে কার্টে পণ্য যোগ করুন।")
        return redirect("core:cart_view")
    if request.method != "POST" and any(
        item["quantity"] > item["product"].stock for item in cart_items
    ):
        messages.error(request, "কার্টে থাকা কোনো পণ্যের পর্যাপ্ত স্টক নেই।")
        return redirect("core:cart_view")

    form = CheckoutForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                locked_products = {
                    str(product.pk): product
                    for product in Product.objects.select_for_update()
                    .filter(pk__in=[int(product_id) for product_id in cart])
                    .order_by("pk")
                }
                if len(locked_products) != len(cart):
                    raise StockUnavailableError

                order_items = []
                order_total = 0
                for product_id, quantity in cart.items():
                    product = locked_products[product_id]
                    if product.stock < quantity:
                        raise StockUnavailableError
                    if product.price < 0:
                        raise InvalidProductPriceError
                    order_items.append(
                        OrderItem(
                            product=product,
                            product_name=product.name,
                            unit_price=product.price,
                            quantity=quantity,
                        )
                    )
                    order_total += product.price * quantity

                customer = form.cleaned_data
                order = Order.objects.create(
                    customer_name=customer["name"],
                    phone=customer["phone"],
                    address=customer["address"],
                    total=order_total,
                )
                for item in order_items:
                    item.order = order
                    item.save()
                for product_id, quantity in cart.items():
                    reserved = Product.objects.filter(
                        pk=locked_products[product_id].pk,
                        stock__gte=quantity,
                    ).update(stock=F("stock") - quantity)
                    if reserved != 1:
                        raise StockUnavailableError
        except StockUnavailableError:
            form.add_error(
                None,
                "কোনো পণ্যের স্টক পরিবর্তিত হয়েছে। কার্টে পরিমাণ যাচাই করে আবার চেষ্টা করুন.",
            )
        except InvalidProductPriceError:
            form.add_error(
                None,
                "পণ্যের দাম সঠিক নয়। Admin থেকে দাম ঠিক করে আবার চেষ্টা করুন।",
            )
        else:
            request.session[CART_SESSION_KEY] = {}
            return redirect(
                "core:order_tracking",
                public_id=order.public_id,
            )

    return render(
        request,
        "checkout.html",
        {
            "form": form,
            "cart_items": cart_items,
            "total_price": total_price,
        },
    )


class StockUnavailableError(Exception):
    pass


class InvalidProductPriceError(Exception):
    pass


def order_tracking(request, public_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        public_id=public_id,
    )
    message_lines = [
        "নতুন অর্ডার - Dada Boys’ Wear",
        f"অর্ডার নম্বর: {order.public_id}",
        "",
        "পণ্যের তালিকা:",
    ]
    for item in order.items.all():
        message_lines.append(
            f"- {item.product_name} x {item.quantity} = ৳{item.line_total}"
        )
    message_lines.append(f"সর্বমোট: ৳{order.total}")
    whatsapp_url = (
        f"https://wa.me/{settings.WHATSAPP_PHONE}?"
        f"{urlencode({'text': chr(10).join(message_lines)})}"
    )
    return render(
        request,
        "order_tracking.html",
        {"order": order, "whatsapp_url": whatsapp_url},
    )
