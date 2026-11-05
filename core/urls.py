from django.urls import path
from . import views

app_name = 'core' # এটাকে বলে URL Namespace, যা প্রজেক্টকে আরও প্রফেশনাল বানায়

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop_catalog, name='shop_catalog'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:pk>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/<uuid:public_id>/', views.order_tracking, name='order_tracking'),
    path('contact/', views.contact, name='contact'),
    path('delivery-policy/', views.delivery_policy, name='delivery_policy'),
    path('about/', views.about, name='about'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
]