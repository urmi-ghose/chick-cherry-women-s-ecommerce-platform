from django.shortcuts import render, redirect
from django.contrib import messages
from store.models import Product, Variation
from .models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OTP,
    PaymentAccount,
    OrderStatusUpdate,
)
from .forms import OrderForm, ShippingForm, OTPForm
from accounts.models import UserProfile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
import uuid
import random
import string
from datetime import timedelta
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import requests
import hashlib
import re
from django.contrib.auth.decorators import login_required
from email_utils import send_email_via_nodemailer

# Create your views here.


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def cart(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        except Cart.DoesNotExist:
            cart_items = []

    total = 0
    quantity = 0
    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        quantity += cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax

    context = {
        "cart_items": cart_items,
        "total": total,
        "quantity": quantity,
        "tax": tax,
        "grand_total": grand_total,
    }
    return render(request, "store/cart.html", context)


@login_required(login_url="accounts:login")
def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        # Handle variations if present
        color = request.POST.get("color")
        size = request.POST.get("size")

        variations = []
        if color:
            try:
                # Use case-insensitive lookup to match stored variation values
                color_variation = Variation.objects.get(
                    product=product,
                    variation_category__name__iexact="color",
                    variation_value__iexact=color,
                )
                variations.append(color_variation)
            except Variation.DoesNotExist:
                pass
        if size:
            try:
                # Use case-insensitive lookup for sizes as well
                size_variation = Variation.objects.get(
                    product=product,
                    variation_category__name__iexact="size",
                    variation_value__iexact=size,
                )
                variations.append(size_variation)
            except Variation.DoesNotExist:
                pass

        # Get or create cart for both authenticated and anonymous users
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))
            cart.save()

        if request.user.is_authenticated:
            existing_items = CartItem.objects.filter(
                product=product, user=request.user, is_active=True
            )
        else:
            existing_items = CartItem.objects.filter(
                product=product, cart=cart, is_active=True
            )

        cart_item = None
        for item in existing_items:
            if set(item.variations.all()) == set(variations):
                cart_item = item
                break

        if cart_item:
            cart_item.quantity += 1
            cart_item.save()
        else:
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart,
            )
            if request.user.is_authenticated:
                cart_item.user = request.user
            cart_item.save()
            cart_item.variations.set(variations)

        # Calculate updated cart count
        cart_count = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                cart_items = CartItem.objects.filter(cart=cart, is_active=True)
            except Cart.DoesNotExist:
                cart_items = []
        for item in cart_items:
            cart_count += item.quantity

        print(f"DEBUG: Cart count calculated: {cart_count}")
        print(
            f"DEBUG: Is AJAX request: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}"
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            response_data = {
                "success": True,
                "message": "Product added to cart successfully!",
                "cart_count": cart_count,
            }
            print(f"DEBUG: Returning JSON response: {response_data}")

            return JsonResponse(response_data)

        else:
            if not request.POST.get("from_cart"):
                messages.success(request, "Product added to cart successfully!")
            if request.POST.get("from_cart"):
                return redirect("carts:cart")
            else:
                return redirect(
                    "product_detail_slug",
                    category_slug=product.category.slug,
                    product_slug=product.slug,
                )
    else:
        return redirect(
            "product_detail_slug",
            category_slug=product.category.slug,
            product_slug=product.slug,
        )


def remove_cart(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(
                product=product, user=request.user, id=cart_item_id
            )
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(
                product=product, cart=cart, id=cart_item_id
            )
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass

    # Calculate updated cart count for AJAX response
    cart_count = 0
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        except Cart.DoesNotExist:
            cart_items = []

    for item in cart_items:
        cart_count += item.quantity

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        response_data = {
            "success": True,
            "message": "Cart updated successfully!",
            "cart_count": cart_count,
        }
        return JsonResponse(response_data)
    else:
        return redirect("carts:cart")


def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(
                product=product, user=request.user, id=cart_item_id
            )
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(
                product=product, cart=cart, id=cart_item_id
            )
        cart_item.delete()
    except:
        pass

    # Calculate updated cart count for AJAX response
    cart_count = 0
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        except Cart.DoesNotExist:
            cart_items = []

    for item in cart_items:
        cart_count += item.quantity

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        response_data = {
            "success": True,
            "message": "Product removed from cart successfully!",
            "cart_count": cart_count,
        }
        return JsonResponse(response_data)
    else:
        return redirect("carts:cart")


def send_otp_ajax(request):
    if request.method == "POST" and request.is_ajax():
        email = request.POST.get("email")
        if email:
            # Generate OTP
            otp_code = "".join(random.choices(string.digits, k=6))
            expires_at = timezone.now() + timedelta(minutes=10)

            # Delete any existing OTP for this email to avoid duplicates
            OTP.objects.filter(email=email).delete()

            # Save OTP to DB
            otp_obj, created = OTP.objects.update_or_create(
                email=email,
                defaults={
                    "otp_code": otp_code,
                    "expires_at": expires_at,
                    "created_at": timezone.now(),
                },
            )

            # Send OTP email
            subject = "Your OTP Code"
            message = f"Your OTP code is {otp_code}. It will expire in 10 minutes."
            send_email_via_nodemailer(
                to_email=email, subject=subject, html_content=None, text_content=message
            )

            return JsonResponse(
                {"status": "success", "message": "OTP sent successfully."}
            )
        else:
            return JsonResponse({"status": "error", "message": "Email is required."})
    else:
        return JsonResponse({"status": "error", "message": "Invalid request."})


@login_required(login_url="accounts:login")
def clear_shipping(request):
    if "shipping_data" in request.session:
        del request.session["shipping_data"]
        request.session.modified = True
    return redirect("carts:checkout")


@login_required(login_url="accounts:login")
def checkout(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        except Cart.DoesNotExist:
            cart_items = []

    total = 0
    quantity = 0
    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        quantity += cart_item.quantity
    tax = (2 * total) / 100
    grand_total = total + tax

    shipping_data = request.session.get("shipping_data")

    if shipping_data:
        # Step 2: OTP verification
        if request.method == "POST":
            form = OTPForm(shipping_data["email"], request.POST)
            if form.is_valid():
                # Save order with shipping_data and email_verified=True
                data = Order()
                data.user = request.user if request.user.is_authenticated else None
                data.first_name = shipping_data["first_name"]
                data.last_name = shipping_data["last_name"]
                data.phone = shipping_data["phone"]
                data.email = shipping_data["email"]
                data.address_line_1 = shipping_data["address_line_1"]
                data.address_line_2 = shipping_data["address_line_2"]
                data.city = shipping_data["city"]
                data.state = shipping_data["state"]
                data.country = shipping_data["country"]
                data.order_note = shipping_data["order_note"]
                data.additional_info = shipping_data["additional_info"]
                data.order_total = grand_total
                data.tax = tax
                data.ip = request.META.get("REMOTE_ADDR")
                data.email_verified = True
                data.created_at = timezone.now()
                data.save()

                # Generate order number
                yr = int(data.created_at.strftime("%Y"))
                dt = int(data.created_at.strftime("%d"))
                mt = int(data.created_at.strftime("%m"))
                d = data.created_at.strftime("%Y%m%d")
                current_date = d
                order_number = current_date + str(data.id)
                data.order_number = order_number
                data.status = "Placed"
                data.save()

                # Create initial status update after saving the order
                OrderStatusUpdate.objects.create(
                    order=data,
                    status="Placed",
                )
                data.save()

                # If user is authenticated, save address to profile
                if request.user.is_authenticated:
                    try:
                        profile = UserProfile.objects.get(user=request.user)
                        profile.address_line_1 = data.address_line_1
                        profile.address_line_2 = data.address_line_2
                        profile.city = data.city
                        profile.state = data.state
                        profile.country = data.country
                        profile.save()
                    except UserProfile.DoesNotExist:
                        profile = UserProfile.objects.create(
                            user=request.user,
                            address_line_1=data.address_line_1,
                            address_line_2=data.address_line_2,
                            city=data.city,
                            state=data.state,
                            country=data.country,
                        )
                        profile.save()

                # Move cart items to OrderItem
                for cart_item in cart_items:
                    order_item = OrderItem()
                    order_item.order = data
                    order_item.product = cart_item.product
                    order_item.quantity = cart_item.quantity
                    order_item.product_price = cart_item.product.price
                    order_item.ordered = True
                    order_item.save()
                    order_item.variations.set(cart_item.variations.all())

                # Clear cart
                cart_items.delete()

                # Clear session
                del request.session["shipping_data"]

                messages.success(request, "Order placed successfully!")
                return redirect("carts:payment", order_id=data.id)
        else:
            form = OTPForm(shipping_data["email"])
        step = "otp"
    else:
        # Step 1: Shipping form
        if request.method == "POST":
            print(f"DEBUG CHECKOUT POST: {request.POST}")
            form = ShippingForm(request.POST)
            print(f"DEBUG: Form is valid: {form.is_valid()}")  # Debug print
            if not form.is_valid():
                print(f"DEBUG: Form errors: {form.errors}")  # Debug print
            if form.is_valid():
                # Store shipping data in session
                request.session["shipping_data"] = {
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                    "phone": form.cleaned_data["phone"],
                    "email": form.cleaned_data["email"],
                    "address_line_1": form.cleaned_data["address_line_1"],
                    "address_line_2": form.cleaned_data["address_line_2"],
                    "city": form.cleaned_data["city"],
                    "state": form.cleaned_data["state"],
                    "country": form.cleaned_data["country"],
                    "order_note": form.cleaned_data["order_note"],
                    "additional_info": form.cleaned_data["additional_info"],
                }
                # Send OTP
                email = form.cleaned_data["email"]
                otp_code = "".join(random.choices(string.digits, k=6))
                expires_at = timezone.now() + timedelta(minutes=10)
                OTP.objects.filter(email=email).delete()
                OTP.objects.update_or_create(
                    email=email,
                    defaults={"otp_code": otp_code, "expires_at": expires_at},
                )
                subject = "Your OTP Code"
                message = f"Your OTP code is {otp_code}. It will expire in 10 minutes."
                print(f"DEBUG: Sending OTP {otp_code} to {email}")
                sent = False
                try:
                    sent = send_email_via_nodemailer(
                        to_email=email,
                        subject=subject,
                        html_content=None,
                        text_content=message,
                    )
                    print(f"DEBUG OTP SEND RESULT: sent={sent} to={email} otp={otp_code}")
                except Exception as e:
                    print(f"DEBUG OTP SEND EXCEPTION: {e}")
                
                if not sent:
                    try:
                        from django.core.mail import send_mail
                        send_mail(
                            subject,
                            message,
                            settings.EMAIL_HOST_USER,
                            [email],
                            fail_silently=False,
                        )
                        sent = True
                    except Exception as e:
                        print(f"DEBUG OTP SEND DJANGO EXCEPTION: {e}")

                if not sent:
                    if settings.DEBUG:
                        messages.warning(request, f"DEBUG MODE: Email failed to send. Your OTP is: {otp_code}")
                        return redirect("carts:checkout")
                    else:
                        messages.error(request, "Failed to send OTP email. Please check your email address or try again later.")
                        return render(request, "store/checkout.html", {
                            "cart_items": cart_items, "total": total, "quantity": quantity,
                            "tax": tax, "grand_total": grand_total, "form": form, "step": "shipping",
                        })
                messages.success(request, "OTP sent to your email. Please enter it to proceed.")
                return redirect("carts:checkout")
        else:
            initial = {}
            if request.user.is_authenticated:
                initial = {
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                    "phone": request.user.phone_number,
                    "email": request.user.email,
                }
                try:
                    profile = UserProfile.objects.get(user=request.user)
                    initial.update({
                        "address_line_1": profile.address_line_1,
                        "address_line_2": profile.address_line_2,
                        "city": profile.city,
                        "state": profile.state,
                        "country": profile.country,
                    })
                except UserProfile.DoesNotExist:
                    pass
            form = ShippingForm(initial=initial)
            if request.user.is_authenticated:
                for field in ["first_name", "last_name", "phone", "email"]:
                    form.fields[field].widget.attrs["readonly"] = True
        step = "shipping"

    context = {
        "cart_items": cart_items,
        "total": total,
        "quantity": quantity,
        "tax": tax,
        "grand_total": grand_total,
        "form": form,
        "step": step,
    }
    return render(request, "store/checkout.html", context)


def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Ensure only the order owner or authenticated user can access
    if order.user and order.user != request.user:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("cart")

    # Block access if order is already confirmed/completed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    order_items = OrderItem.objects.filter(order=order)

    payment_methods = [
        ("visa", "Visa"),
        ("mastercard", "Mastercard"),
        ("rocket", "Rocket"),
        ("bkash", "bKash"),
        ("upay", "Upay"),
        ("nogod", "Nogod"),
    ]

    payment_images = {
        "visa": "paymentImg/visa-new-2021-logo-png_seeklogo-408695.png",
        "mastercard": "paymentImg/American-Express-Logo-Download-Free-PNG.png",
        "rocket": "paymentImg/images.png",
        "bkash": "paymentImg/images.jpg",
        "upay": "paymentImg/png-transparent-paypal-logo-paypal-logo-paypal-blue-text-trademark.png",
        "nogod": "paymentImg/নগদের_লোগো.png",
    }

    saved_accounts = {}
    if request.user.is_authenticated:
        from .models import PaymentAccount

        for method, _ in payment_methods:
            try:
                saved_accounts[method] = PaymentAccount.objects.get(
                    user=request.user, payment_method=method
                )
            except PaymentAccount.DoesNotExist:
                saved_accounts[method] = None

    payment_options = []
    for method, name in payment_methods:
        payment_options.append(
            {
                "method": method,
                "name": name,
                "image": payment_images[method],
                "saved_account": saved_accounts.get(method, None),
            }
        )

    context = {
        "order": order,
        "order_items": order_items,
        "payment_options": payment_options,
    }
    return render(request, "store/payment.html", context)


def confirm_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Check if order is already confirmed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    # Simulate payment success
    order.status = "Completed"
    order.save()

    # Send order confirmation email
    order_items = OrderItem.objects.filter(order=order)
    items_list = "\n".join(
        [
            f"{item.product.product_name} - Quantity: {item.quantity} - Price: ${item.product_price}"
            for item in order_items
        ]
    )

    subject = "Order Confirmation"
    message = f"""Order Confirmation
Thank you for your order!
Order Number: {order.order_number}

Status: {order.status}

Total Amount: ${order.order_total}

Order Items:
{items_list}
Shipping Address:
{order.first_name} {order.last_name}

{order.address_line_1}
{order.address_line_2}

{order.city}, {order.state}, {order.country}

Phone: {order.phone}

Email: {order.email}
"""
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [order.email]
    try:
        send_email_via_nodemailer(
            to_email=order.email,
            subject=subject,
            html_content=None,
            text_content=message,
        )
    except Exception as e:
        print(f"DEBUG: Failed to send confirmation email to {order.email}: {e}")
        messages.warning(
            request,
            "Payment confirmed, but confirmation email could not be sent due to email service issues.",
        )

    messages.success(request, "Payment successful! Order confirmed.")
    return redirect("carts:confirmation", order_id=order.id)


def confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    # Check if this is the first time viewing the confirmation
    session_key = f"confirmation_viewed_{order_id}"
    first_time = not request.session.get(session_key, False)
    if first_time:
        request.session[session_key] = True
        already_confirmed = False
    else:
        already_confirmed = True

    context = {
        "order": order,
        "order_items": order_items,
        "already_confirmed": already_confirmed,
    }
    return render(request, "store/confirmation.html", context)


def validate_account_number(account_number, method):
    """Validate account number based on payment method."""
    if method == "visa":
        if not re.match(r"^\d{13,16}$", account_number):
            return False
    elif method == "mastercard":
        if not re.match(r"^\d{16}$", account_number):
            return False
    elif method == "rocket":
        if not re.match(r"^\d{10,16}$", account_number):
            return False
    elif method in ["bkash", "upay", "nogod"]:
        if not re.match(r"^\d{11}$", account_number):
            return False
    else:
        return False
    return True


# Payment Method Views
def visa_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to use payment methods.")
        return redirect("accounts:login")

    # Check if order is already confirmed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    if request.method == "POST":
        use_saved = request.POST.get("use_saved")
        account_number = request.POST.get("account_number")

        if use_saved:
            try:
                payment_account = PaymentAccount.objects.get(
                    user=request.user, payment_method="visa"
                )
                account_number = payment_account.account_number
            except PaymentAccount.DoesNotExist:
                messages.error(
                    request, "No saved Visa account found. Please enter account number."
                )
                return redirect("carts:payment", order_id=order_id)
        else:
            if not account_number or not validate_account_number(
                account_number, "visa"
            ):
                messages.error(
                    request,
                    "Invalid Visa account number. Please enter a 13-16 digit number.",
                )
                return redirect("carts:payment", order_id=order_id)
            # Save the account number for future use
            PaymentAccount.objects.update_or_create(
                user=request.user,
                payment_method="visa",
                defaults={"account_number": account_number},
            )

    # Simulate Visa payment success
    order.status = "Processing"
    order.payment_status = "Paid"
    order.save()

    # Create status update
    OrderStatusUpdate.objects.create(
        order=order, status="Processing", notes="Payment received via Visa"
    )

    # Send confirmation email
    order_items = OrderItem.objects.filter(order=order)
    items_list = "\n".join(
        [
            f"{item.product.product_name} - Quantity: {item.quantity} - Price: ${item.product_price}"
            for item in order_items
        ]
    )

    subject = "Order Confirmation"
    message = f"""Order Confirmation
Thank you for your order!
Order Number: {order.order_number}

Status: {order.status}

Total Amount: ${order.order_total}

Order Items:
{items_list}
Shipping Address:
{order.first_name} {order.last_name}

{order.address_line_1}
{order.address_line_2}

{order.city}, {order.state}, {order.country}

Phone: {order.phone}

Email: {order.email}
"""
    try:
        send_email_via_nodemailer(
            to_email=order.email,
            subject=subject,
            html_content=None,
            text_content=message,
        )
    except Exception as e:
        print(f"DEBUG: Failed to send confirmation email to {order.email}: {e}")
        messages.warning(
            request,
            "Payment confirmed, but confirmation email could not be sent due to email service issues.",
        )

    messages.success(request, "Payment successful via Visa! Order confirmed.")
    return redirect("carts:confirmation", order_id=order.id)


def rocket_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to use payment methods.")
        return redirect("accounts:login")

    # Check if order is already confirmed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    if request.method == "POST":
        use_saved = request.POST.get("use_saved")
        account_number = request.POST.get("account_number")

        if use_saved:
            try:
                payment_account = PaymentAccount.objects.get(
                    user=request.user, payment_method="rocket"
                )
                account_number = payment_account.account_number
            except PaymentAccount.DoesNotExist:
                messages.error(
                    request,
                    "No saved Rocket account found. Please enter account number.",
                )
                return redirect("carts:payment", order_id=order_id)
        else:
            if not account_number or not validate_account_number(
                account_number, "rocket"
            ):
                messages.error(
                    request,
                    "Invalid Rocket account number. Please enter a 10-16 digit number.",
                )
                return redirect("carts:payment", order_id=order_id)
            # Save the account number for future use
            PaymentAccount.objects.update_or_create(
                user=request.user,
                payment_method="rocket",
                defaults={"account_number": account_number},
            )

    # Simulate Rocket payment success
    order.status = "Processing"
    order.payment_status = "Paid"
    order.save()

    # Create status update
    OrderStatusUpdate.objects.create(
        order=order, status="Processing", notes="Payment received via Rocket"
    )

    # Send confirmation email
    order_items = OrderItem.objects.filter(order=order)
    items_list = "\n".join(
        [
            f"{item.product.product_name} - Quantity: {item.quantity} - Price: ${item.product_price}"
            for item in order_items
        ]
    )

    subject = "Order Confirmation"
    message = f"""Order Confirmation
Thank you for your order!
Order Number: {order.order_number}

Status: {order.status}

Total Amount: ${order.order_total}

Order Items:
{items_list}
Shipping Address:
{order.first_name} {order.last_name}

{order.address_line_1}
{order.address_line_2}

{order.city}, {order.state}, {order.country}

Phone: {order.phone}

Email: {order.email}
"""
    try:
        send_email_via_nodemailer(
            to_email=order.email,
            subject=subject,
            html_content=None,
            text_content=message,
        )
    except Exception as e:
        print(f"DEBUG: Failed to send confirmation email to {order.email}: {e}")
        messages.warning(
            request,
            "Payment confirmed, but confirmation email could not be sent due to email service issues.",
        )

    messages.success(request, "Payment successful via Rocket! Order confirmed.")
    return redirect("carts:confirmation", order_id=order.id)


def mastercard_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to use payment methods.")
        return redirect("accounts:login")

    # Check if order is already confirmed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    if request.method == "POST":
        use_saved = request.POST.get("use_saved")
        account_number = request.POST.get("account_number")

        if use_saved:
            try:
                payment_account = PaymentAccount.objects.get(
                    user=request.user, payment_method="mastercard"
                )
                account_number = payment_account.account_number
            except PaymentAccount.DoesNotExist:
                messages.error(
                    request,
                    "No saved Mastercard account found. Please enter account number.",
                )
                return redirect("carts:payment", order_id=order_id)
        else:
            if not account_number or not validate_account_number(
                account_number, "mastercard"
            ):
                messages.error(
                    request,
                    "Invalid Mastercard account number. Please enter a 16 digit number.",
                )
                return redirect("carts:payment", order_id=order_id)
            # Save the account number for future use
            PaymentAccount.objects.update_or_create(
                user=request.user,
                payment_method="mastercard",
                defaults={"account_number": account_number},
            )

    # Simulate Mastercard payment success
    order.status = "Processing"
    order.payment_status = "Paid"
    order.save()

    # Create status update
    OrderStatusUpdate.objects.create(
        order=order, status="Processing", notes="Payment received via Mastercard"
    )

    # Send confirmation email
    order_items = OrderItem.objects.filter(order=order)
    items_list = "\n".join(
        [
            f"{item.product.product_name} - Quantity: {item.quantity} - Price: ${item.product_price}"
            for item in order_items
        ]
    )

    subject = "Order Confirmation"
    message = f"""Order Confirmation
Thank you for your order!
Order Number: {order.order_number}

Status: {order.status}

Total Amount: ${order.order_total}

Order Items:
{items_list}
Shipping Address:
{order.first_name} {order.last_name}

{order.address_line_1}
{order.address_line_2}

{order.city}, {order.state}, {order.country}

Phone: {order.phone}

Email: {order.email}
"""
    try:
        send_email_via_nodemailer(
            to_email=order.email,
            subject=subject,
            html_content=None,
            text_content=message,
        )
    except Exception as e:
        print(f"DEBUG: Failed to send confirmation email to {order.email}: {e}")
        messages.warning(
            request,
            "Payment confirmed, but confirmation email could not be sent due to email service issues.",
        )

    messages.success(request, "Payment successful via Mastercard! Order confirmed.")
    return redirect("carts:confirmation", order_id=order.id)


def bkash_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to use payment methods.")
        return redirect("accounts:login")

    # Check if order is already confirmed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    if request.method == "POST":
        use_saved = request.POST.get("use_saved")
        account_number = request.POST.get("account_number")

        if use_saved:
            try:
                payment_account = PaymentAccount.objects.get(
                    user=request.user, payment_method="bkash"
                )
                account_number = payment_account.account_number
            except PaymentAccount.DoesNotExist:
                messages.error(
                    request,
                    "No saved bKash account found. Please enter account number.",
                )
                return redirect("carts:payment", order_id=order_id)
        else:
            if not account_number or not validate_account_number(
                account_number, "bkash"
            ):
                messages.error(
                    request,
                    "Invalid bKash account number. Please enter an 11 digit number.",
                )
                return redirect("carts:payment", order_id=order_id)
            # Save the account number for future use
            PaymentAccount.objects.update_or_create(
                user=request.user,
                payment_method="bkash",
                defaults={"account_number": account_number},
            )

    # Simulate bKash payment success
    order.status = "Processing"
    order.payment_status = "Paid"
    order.save()

    # Create status update
    OrderStatusUpdate.objects.create(
        order=order, status="Processing", notes="Payment received via bKash"
    )

    # Send confirmation email
    order_items = OrderItem.objects.filter(order=order)
    items_list = "\n".join(
        [
            f"- {item.product.product_name} x {item.quantity} @ ${item.product_price} each"
            for item in order_items
        ]
    )

    subject = f"Order Confirmation - Order #{order.order_number}"
    message = f"""
Dear {order.first_name} {order.last_name},

Your order has been confirmed and payment received via bKash.

Order Number: {order.order_number}
Order Date: {order.created_at.strftime("%Y-%m-%d %H:%M:%S")}
Total: ${order.order_total}

Items:
{items_list}

Shipping Address:
{order.address_line_1}
{order.address_line_2}
{order.city}, {order.state}, {order.country}

Thank you for shopping with us!
"""
    try:
        send_email_via_nodemailer(
            to_email=order.email,
            subject=subject,
            html_content=None,
            text_content=message,
        )
    except Exception as e:
        print(f"DEBUG: Failed to send confirmation email to {order.email}: {e}")
        messages.warning(
            request,
            "Payment confirmed, but confirmation email could not be sent due to email service issues.",
        )

    messages.success(request, "Payment successful via bKash! Order confirmed.")
    return redirect("carts:confirmation", order_id=order.id)


def upay_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to use payment methods.")
        return redirect("accounts:login")

    # Check if order is already confirmed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    if request.method == "POST":
        use_saved = request.POST.get("use_saved")
        account_number = request.POST.get("account_number")

        if use_saved:
            try:
                payment_account = PaymentAccount.objects.get(
                    user=request.user, payment_method="upay"
                )
                account_number = payment_account.account_number
            except PaymentAccount.DoesNotExist:
                messages.error(
                    request, "No saved Upay account found. Please enter account number."
                )
                return redirect("carts:payment", order_id=order_id)
        else:
            if not account_number or not validate_account_number(
                account_number, "upay"
            ):
                messages.error(
                    request,
                    "Invalid Upay account number. Please enter an 11 digit number.",
                )
                return redirect("carts:payment", order_id=order_id)
            # Save the account number for future use
            PaymentAccount.objects.update_or_create(
                user=request.user,
                payment_method="upay",
                defaults={"account_number": account_number},
            )

    # Simulate Upay payment success
    order.status = "Processing"
    order.payment_status = "Paid"
    order.save()

    # Create status update
    OrderStatusUpdate.objects.create(
        order=order, status="Processing", notes="Payment received via Upay"
    )

    # Send confirmation email
    order_items = OrderItem.objects.filter(order=order)
    items_list = "\n".join(
        [
            f"- {item.product.product_name} x {item.quantity} @ ${item.product_price} each"
            for item in order_items
        ]
    )

    subject = f"Order Confirmation - Order #{order.order_number}"
    message = f"""
Dear {order.first_name} {order.last_name},

Your order has been confirmed and payment received via Upay.

Order Number: {order.order_number}
Order Date: {order.created_at.strftime("%Y-%m-%d %H:%M:%S")}
Total: ${order.order_total}

Items:
{items_list}

Shipping Address:
{order.address_line_1}
{order.address_line_2}
{order.city}, {order.state}, {order.country}

Thank you for shopping with us!
"""
    try:
        send_email_via_nodemailer(
            to_email=order.email,
            subject=subject,
            html_content=None,
            text_content=message,
        )
    except Exception as e:
        print(f"DEBUG: Failed to send confirmation email to {order.email}: {e}")
        messages.warning(
            request,
            "Payment confirmed, but confirmation email could not be sent due to email service issues.",
        )

    messages.success(request, "Payment successful via Upay! Order confirmed.")
    return redirect("carts:confirmation", order_id=order.id)


def nogod_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to use payment methods.")
        return redirect("accounts:login")

    # Check if order is already confirmed
    if order.status == "Completed" or order.payment_status == "Paid":
        messages.info(
            request, "This order has already been confirmed and payment received."
        )
        return redirect("carts:confirmation", order_id=order.id)

    if request.method == "POST":
        use_saved = request.POST.get("use_saved")
        account_number = request.POST.get("account_number")

        if use_saved:
            try:
                payment_account = PaymentAccount.objects.get(
                    user=request.user, payment_method="nogod"
                )
                account_number = payment_account.account_number
            except PaymentAccount.DoesNotExist:
                messages.error(
                    request,
                    "No saved Nogod account found. Please enter account number.",
                )
                return redirect("carts:payment", order_id=order_id)
        else:
            if not account_number or not validate_account_number(
                account_number, "nogod"
            ):
                messages.error(
                    request,
                    "Invalid Nogod account number. Please enter an 11 digit number.",
                )
                return redirect("carts:payment", order_id=order_id)
            # Save the account number for future use
            PaymentAccount.objects.update_or_create(
                user=request.user,
                payment_method="nogod",
                defaults={"account_number": account_number},
            )

    # Simulate Nogod payment success
    order.status = "Processing"
    order.payment_status = "Paid"
    order.save()

    # Create status update
    OrderStatusUpdate.objects.create(
        order=order, status="Processing", notes="Payment received via Nogod"
    )

    # Send confirmation email
    order_items = OrderItem.objects.filter(order=order)
    items_list = "\n".join(
        [
            f"- {item.product.product_name} x {item.quantity} @ ${item.product_price} each"
            for item in order_items
        ]
    )

    subject = f"Order Confirmation - Order #{order.order_number}"
    message = f"""
Dear {order.first_name} {order.last_name},

Your order has been confirmed and payment received via Nogod.

Order Number: {order.order_number}
Order Date: {order.created_at.strftime("%Y-%m-%d %H:%M:%S")}
Total: ${order.order_total}

Items:
{items_list}

Shipping Address:
{order.address_line_1}
{order.address_line_2}
{order.city}, {order.state}, {order.country}

Thank you for shopping with us!
"""
    try:
        send_email_via_nodemailer(
            to_email=order.email,
            subject=subject,
            html_content=None,
            text_content=message,
        )
    except Exception as e:
        print(f"DEBUG: Failed to send confirmation email to {order.email}: {e}")
        messages.warning(
            request,
            "Payment confirmed, but confirmation email could not be sent due to email service issues.",
        )

    messages.success(request, "Payment successful via Nogod! Order confirmed.")
    return redirect("carts:confirmation", order_id=order.id)


@login_required(login_url="accounts:login")
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    context = {
        "orders": orders,
    }
    return render(request, "store/order_history.html", context)


@login_required(login_url="accounts:login")
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    status_updates = order.status_updates.all()

    context = {
        "order": order,
        "order_items": order_items,
        "status_updates": status_updates,
    }
    return render(request, "store/order_detail.html", context)
