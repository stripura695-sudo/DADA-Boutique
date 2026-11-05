from django.conf import settings

from .models import Product


def shop_contact(request):
    return {
        "shop_whatsapp_phone": settings.WHATSAPP_PHONE,
        "shop_whatsapp_url": f"https://wa.me/{settings.WHATSAPP_PHONE}",
        "shop_menu_products": Product.objects.order_by("name"),
    }
