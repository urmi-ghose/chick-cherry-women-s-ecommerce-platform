from django.db import models
from store.models import Product, Variation
from accounts.models import Account
import random
import string
from datetime import datetime, timedelta
from django.utils import timezone

# Create your models here.


class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)

    def sub_total(self):
        return self.product.price * self.quantity

    def __unicode__(self):
        return self.product


class Order(models.Model):
    STATUS = (
        ("Placed", "Placed"),
        ("Processing", "Processing"),
        ("Shipped", "Shipped"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    )

    PAYMENT_STATUS = (
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Failed", "Failed"),
    )

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    email = models.EmailField(max_length=100)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=50)
    address_line_2 = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    order_note = models.CharField(max_length=100, blank=True)
    additional_info = models.CharField(max_length=255, blank=True)  # New field added
    email_verified = models.BooleanField(
        default=False
    )  # New field for email verification status
    order_total = models.FloatField()
    tax = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS, default="Placed")
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS, default="Pending"
    )
    ip = models.CharField(blank=True, max_length=20)
    order_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def full_address(self):
        return f"{self.address_line_1} {self.address_line_2}"

    def __str__(self):
        return self.first_name


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation, blank=True)
    quantity = models.IntegerField()
    product_price = models.FloatField()
    ordered = models.BooleanField(default=False)

    def __str__(self):
        return self.product.product_name


class PaymentAccount(models.Model):
    PAYMENT_METHODS = (
        ("visa", "Visa"),
        ("mastercard", "Mastercard"),
        ("rocket", "Rocket"),
        ("bkash", "bKash"),
        ("upay", "Upay"),
        ("nogod", "Nogod"),
    )

    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    account_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "payment_method")

    def __str__(self):
        return f"{self.user.email} - {self.payment_method}"

    def masked_account_number(self):
        """Return masked account number showing last 4 digits"""
        if len(self.account_number) > 4:
            return "*" * (len(self.account_number) - 4) + self.account_number[-4:]
        return self.account_number


class OrderStatusUpdate(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_updates"
    )
    status = models.CharField(max_length=10, choices=Order.STATUS)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"Order {self.order.order_number} - {self.status} at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]


class OTP(models.Model):
    email = models.EmailField(max_length=100)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def generate_otp(self):
        """Generate a 6-digit OTP"""
        self.otp_code = "".join(random.choices(string.digits, k=6))
        self.expires_at = timezone.now() + timedelta(
            minutes=10
        )  # OTP expires in 10 minutes
        self.save()

    def is_expired(self):
        """Check if OTP is expired"""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.email}: {self.otp_code}"
