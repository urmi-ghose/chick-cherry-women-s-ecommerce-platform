from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegistrationForm, UserForm, UserProfileForm
from .models import Account, UserProfile
from carts.models import Order, OrderItem as OrderProduct, OTP
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

# Verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, EmailMultiAlternatives

from carts.views import _cart_id
from carts.models import Cart, CartItem
import requests
import time
import smtplib
import json
from email_utils import send_email_via_nodemailer


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            phone_number = form.cleaned_data["phone_number"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Console log the form data
            print("User Registration Form Data:")
            print(f"First Name: {first_name}")
            print(f"Last Name: {last_name}")
            print(f"Phone Number: {phone_number}")
            print(f"Email: {email}")
            print(f"Password: {password}")
            username = email.split("@")[0]
            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password,
            )
            user.phone_number = phone_number
            user.is_active = False  # User is inactive until OTP verification
            user.save()

            # Create a user profile
            profile = UserProfile()
            profile.user_id = user.id
            profile.profile_picture = "default/default-user.png"
            profile.save()

            # Generate and send OTP
            otp_obj = OTP(email=email)
            otp_obj.generate_otp()
            mail_subject = "Account Verification OTP"
            html_message = render_to_string(
                "accounts/otp_verification_email.html",
                {
                    "user": user,
                    "otp": otp_obj.otp_code,
                },
            )
            plain_message = f"Dear {user.first_name},\n\nYour OTP for account verification is: {otp_obj.otp_code}.\n\nThis OTP will expire in 10 minutes.\n\nPlease enter this OTP on the verification page to activate your account.\n\nIf you did not request this, please ignore this email.\n\nBest regards,\nChicCherry Team"
            to_email = email
            send_email = EmailMultiAlternatives(
                mail_subject, plain_message, to=[to_email]
            )
            send_email.attach_alternative(html_message, "text/html")

            # Try sending email via nodemailer service first, fallback to Django if needed
            email_sent = send_email_via_nodemailer(
                to_email, mail_subject, html_message, plain_message
            )

            if not email_sent:
                # Fallback to Django's email system with retry logic
                max_retries = 3
                retry_delay = 1  # Start with 1 second
                for attempt in range(max_retries):
                    try:
                        send_email.send()
                        email_sent = True
                        break  # Success, exit loop
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(
                                f"Email send failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay} seconds..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            print(
                                f"Email send failed after {max_retries} attempts: {e}. Proceeding with OTP verification."
                            )
                if not email_sent:
                    messages.warning(
                        request,
                        "We encountered an issue sending the email. Please check your email later or use the resend OTP option.",
                    )

            messages.success(
                request,
                "Thank you for registering with us. We have sent you an OTP to your email address. Please verify it.",
            )
            request.session['otp_email'] = email
            return redirect("accounts:verify_otp")
    else:
        form = RegistrationForm()
    context = {
        "form": form,
    }
    return render(request, "accounts/register.html", context)


def login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)

                    # Getting the product variations by cart id
                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))

                    # Get the cart items from the user to access his product variations
                    cart_item = CartItem.objects.filter(user=user)
                    ex_var_list = []
                    id = []
                    for item in cart_item:
                        existing_variation = item.variations.all()
                        ex_var_list.append(list(existing_variation))
                        id.append(item.id)

                    # product_variation = [1, 2, 3, 4, 6]
                    # ex_var_list = [4, 6, 3, 5]

                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart)
                            for item in cart_item:
                                item.user = user
                                item.save()
            except:
                pass
            auth.login(request, user)
            messages.success(request, "You are now logged in.")
            url = request.META.get("HTTP_REFERER")
            try:
                query = requests.utils.urlparse(url).query
                # next=/cart/checkout/
                params = dict(x.split("=") for x in query.split("&"))
                if "next" in params:
                    nextPage = params["next"]
                    return redirect(nextPage)
            except:
                return redirect("accounts:dashboard")
        else:
            messages.error(request, "Invalid login credentials")
            return redirect("accounts:login")
    return render(request, "accounts/login.html")


@login_required(login_url="accounts:login")
def logout(request):
    auth.logout(request)
    messages.error(request, "You have been logged out.")
    return redirect("home")


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Congratulations! Your account is activated.")
        return redirect("accounts:login")
    else:
        messages.error(request, "Invalid activation link")
        return redirect("accounts:register")


@login_required(login_url="accounts:login")
def dashboard(request):
    orders = Order.objects.order_by("-created_at").filter(user_id=request.user.id)
    orders_count = orders.count()

    try:
        userprofile = UserProfile.objects.get(user_id=request.user.id)
    except UserProfile.DoesNotExist:
        userprofile = None

    context = {
        "orders_count": orders_count,
        "userprofile": userprofile,
    }
    return render(request, "accounts/dashboard.html", context)


def forgotPassword(request):
    if request.method == "POST":
        email = request.POST["email"]
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)

            # Reset password email
            current_site = get_current_site(request)
            mail_subject = "Reset Your Password"
            message = render_to_string(
                "accounts/reset_password_email.html",
                {
                    "user": user,
                    "domain": current_site,
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": default_token_generator.make_token(user),
                },
            )
            to_email = email
            reset_url = f"http://{current_site}{message}"
            plain_message = f"Hi {user.first_name},\n\nPlease click the link below to reset your password:\n\n{reset_url}\n\nIf you did not request a password reset, please ignore this email.\n\nBest regards,\nChicCherry Team"
            send_email = EmailMultiAlternatives(
                mail_subject, plain_message, to=[to_email]
            )
            send_email.attach_alternative(message, "text/html")

            send_email.send()

            messages.success(
                request, "Password reset email has been sent to your email address."
            )
            return redirect("accounts:login")
        else:
            messages.error(request, "Account does not exist!")
            return redirect("accounts:forgotPassword")
    return render(request, "accounts/forgotPassword.html")


def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session["uid"] = uid
        messages.success(request, "Please reset your password")
        return redirect("accounts:resetPassword")
    else:
        messages.error(request, "This link has been expired!")
        return redirect("accounts:login")


def resetPassword(request):
    if request.method == "POST":
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password == confirm_password:
            uid = request.session.get("uid")
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, "Password reset successful")
            return redirect("accounts:login")
        else:
            messages.error(request, "Password do not match!")
            return redirect("accounts:resetPassword")
    else:
        return render(request, "accounts/resetPassword.html")


@login_required(login_url="accounts:login")
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    context = {
        "orders": orders,
    }
    return render(request, "accounts/my_orders.html", context)


@login_required(login_url="accounts:login")
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=userprofile
        )
        if user_form.is_valid() and profile_form.is_valid():
            try:
                user_form.save()
                profile_form.save()
                messages.success(request, "Your profile has been updated.")
                return redirect("accounts:edit_profile")
            except Exception as e:
                messages.error(request, f"Upload failed: {str(e)}. Please try again.")
                return redirect("accounts:edit_profile")
        else:
            # Handle form validation errors
            if not profile_form.is_valid():
                for field, errors in profile_form.errors.items():
                    for error in errors:
                        messages.error(request, f"Profile {field}: {error}")
            if not user_form.is_valid():
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f"User {field}: {error}")
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "userprofile": userprofile,
    }
    return render(request, "accounts/edit_profile.html", context)


@login_required(login_url="accounts:login")
def change_password(request):
    if request.method == "POST":
        current_password = request.POST["current_password"]
        new_password = request.POST["new_password"]
        confirm_password = request.POST["confirm_password"]

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                # auth.logout(request)
                messages.success(request, "Password updated successfully.")
                return redirect("accounts:change_password")
            else:
                messages.error(request, "Please enter valid current password")
                return redirect("accounts:change_password")
        else:
            messages.error(request, "Password does not match!")
            return redirect("accounts:change_password")
    return render(request, "accounts/change_password.html")


@login_required(login_url="accounts:login")
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderProduct.objects.filter(order=order)
    status_updates = order.status_updates.all()

    subtotal = 0
    for item in order_items:
        item.total = item.product_price * item.quantity
        subtotal += item.total

    context = {
        "order": order,
        "order_items": order_items,
        "status_updates": status_updates,
        "subtotal": subtotal,
    }
    return render(request, "store/order_detail.html", context)


def verify_otp(request):
    if request.method == "POST":
        otp_code = request.POST.get("otp")
        if otp_code:
            try:
                otp_obj = OTP.objects.filter(otp_code=otp_code).latest("created_at")
                if otp_obj and not otp_obj.is_expired():
                    user = Account.objects.get(email=otp_obj.email)
                    user.is_active = True
                    user.save()
                    otp_obj.delete()
                    request.session.pop('otp_email', None)
                    messages.success(
                        request,
                        "Your account has been successfully verified. Welcome to ChicCherry!",
                    )
                    auth.login(request, user)
                    return redirect("accounts:dashboard")
                else:
                    messages.error(request, "Invalid or expired OTP.")
            except OTP.DoesNotExist:
                messages.error(request, "Invalid OTP.")
            except Account.DoesNotExist:
                messages.error(request, "Account not found.")
        else:
            messages.error(request, "Please enter the OTP.")
    otp_email = request.session.get('otp_email', '')
    return render(request, "accounts/otp_verification.html", {'otp_email': otp_email})


def resend_otp(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            try:
                user = Account.objects.get(email=email, is_active=False)
                otp_obj = OTP(email=email)
                otp_obj.generate_otp()
                mail_subject = "Account Verification OTP"
                html_message = render_to_string(
                    "accounts/otp_verification_email.html",
                    {
                        "user": user,
                        "otp": otp_obj.otp_code,
                    },
                )
                plain_message = f"Dear {user.first_name},\n\nYour OTP for account verification is: {otp_obj.otp_code}.\n\nThis OTP will expire in 10 minutes.\n\nPlease enter this OTP on the verification page to activate your account.\n\nIf you did not request this, please ignore this email.\n\nBest regards,\nChicCherry Team"
                to_email = email
                send_email = EmailMultiAlternatives(
                    mail_subject, plain_message, to=[to_email]
                )
                send_email.attach_alternative(html_message, "text/html")

                # Try sending email via nodemailer service first, fallback to Django if needed
                email_sent = send_email_via_nodemailer(
                    to_email, mail_subject, html_message, plain_message
                )

                if not email_sent:
                    # Fallback to Django's email system with retry logic
                    max_retries = 3
                    retry_delay = 1  # Start with 1 second
                    for attempt in range(max_retries):
                        try:
                            send_email.send()
                            email_sent = True
                            break  # Success, exit loop
                        except smtplib.SMTPRecipientsRefused as e:
                            if attempt < max_retries - 1:
                                print(
                                    f"Email send failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay} seconds..."
                                )
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                print(
                                    f"Email send failed after {max_retries} attempts: {e}. Proceeding with OTP verification."
                                )
                    if not email_sent:
                        messages.warning(
                            request,
                            "We encountered an issue sending the email. Please check your email later or use the resend OTP option.",
                        )
                messages.success(
                    request, "A new OTP has been sent to your email address."
                )
            except Account.DoesNotExist:
                messages.error(request, "No inactive account found with this email.")
        else:
            messages.error(request, "Please provide an email address.")
    return redirect("accounts:verify_otp")
