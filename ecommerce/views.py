from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from store.models import Product
from store.views import store as store_view
from category.models import Category

def home(request):
    from store.models import SliderItem
    products = Product.objects.filter(is_available=True).exclude(product_name__icontains='Shirt').exclude(product_name__icontains='Scarf')[:8]
    footwear_products = (Product.objects.filter(is_available=True, product_name__icontains='sandal') |
                         Product.objects.filter(is_available=True, product_name__icontains='canvas') |
                         Product.objects.filter(is_available=True, product_name__icontains='slipper') |
                         Product.objects.filter(is_available=True, product_name__icontains='pamp') |
                         Product.objects.filter(is_available=True, product_name__icontains='sports shoe'))[:8]
    discount_products = list(Product.objects.filter(is_available=True, discount_percent__gt=0).order_by('?')[:4])
    links = Category.objects.all()
    slider_items = SliderItem.objects.filter(is_active=True)
    return render(request, "home.html", {'products': products, 'footwear_products': footwear_products, 'discount_products': discount_products, 'links': links, 'slider_items': slider_items})

def store(request):
    return store_view(request)

def cart(request):
    return render(request, "cart.html")

def product_detail(request, product_id):
    return render(request, "product_detail.html", {'product_id': product_id})

