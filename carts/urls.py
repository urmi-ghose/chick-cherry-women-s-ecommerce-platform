from django.urls import path
from . import views

app_name = 'carts'

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add/<int:product_id>/', views.add_cart, name='add_cart'),
    path('remove/<int:product_id>/<int:cart_item_id>/', views.remove_cart, name='remove_cart'),
    path('remove_item/<int:product_id>/<int:cart_item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/reset/', views.clear_shipping, name='clear_shipping'),
    path('send_otp/', views.send_otp_ajax, name='send_otp'),
    path('payment/<int:order_id>/', views.payment, name='payment'),
    path('confirm_payment/<int:order_id>/', views.confirm_payment, name='confirm_payment'),
    path('confirmation/<int:order_id>/', views.confirmation, name='confirmation'),

    # Payment Method URLs
    path('visa_payment/<int:order_id>/', views.visa_payment, name='visa_payment'),
    path('rocket_payment/<int:order_id>/', views.rocket_payment, name='rocket_payment'),
    path('mastercard_payment/<int:order_id>/', views.mastercard_payment, name='mastercard_payment'),
    path('bkash_payment/<int:order_id>/', views.bkash_payment, name='bkash_payment'),
    path('upay_payment/<int:order_id>/', views.upay_payment, name='upay_payment'),
    path('nogod_payment/<int:order_id>/', views.nogod_payment, name='nogod_payment'),

    # Order tracking URLs
    path('order_history/', views.order_history, name='order_history'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),
]
