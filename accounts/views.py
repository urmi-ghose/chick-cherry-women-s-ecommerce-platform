from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegistrationForm, UserForm, UserProfileForm
from .models import Account, UserProfile
from carts.models import Order, OrderItem as OrderProduct, OTP, PaymentAccount
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import re
import secrets
import urllib.parse

# Verification email
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, EmailMultiAlternatives

from carts.views import _cart_id, validate_account_number
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


def _merge_cart(request, user):
    """
    Merge guest session cart items into authenticated user's cart.
    Matches variations and products so existing user items get increased quantity,
    and unmatched items are reassigned to user.
    """
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        session_cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        if not session_cart_items.exists():
            return

        for s_item in list(session_cart_items):
            s_vars = list(s_item.variations.all())
            user_cart_items = CartItem.objects.filter(user=user, is_active=True)
            matched = False
            for u_item in user_cart_items:
                u_vars = list(u_item.variations.all())
                if s_vars == u_vars and s_item.product == u_item.product:
                    u_item.quantity += s_item.quantity
                    u_item.save()
                    s_item.delete()
                    matched = True
                    break
            if not matched:
                s_item.user = user
                s_item.save()
    except Exception:
        pass


def _generate_unique_username(email, first_name="", last_name=""):
    """
    Generate a clean, unique username under 50 characters for the Account model.
    """
    base = ""
    if email and "@" in email:
        base = email.split("@")[0]
    elif first_name:
        base = f"{first_name}_{last_name}".strip("_")
    else:
        base = "user"

    base = re.sub(r"[^a-zA-Z0-9_]", "", base).lower()[:30] or "user"
    username = base
    counter = 1
    while Account.objects.filter(username__iexact=username).exists():
        suffix = str(counter)
        max_base = 50 - len(suffix) - 1
        username = f"{base[:max_base]}_{suffix}"
        counter += 1
    return username


def _handle_google_user(request, email, first_name="", last_name="", picture_url="", allow_create=False):
    """
    Smartly handle Google authentication:
    - Normalizes Gmail address.
    - If user exists in Account table:
        Activates account if inactive, updates names if empty,
        ensures UserProfile exists, merges cart, and logs user in.
        Returns (user, False, None) -> (user, created, error_message)
    - If user does NOT exist in Account table:
        If allow_create is False (default for login):
            DOES NOT register automatically!
            Returns (None, False, error_message)
        If allow_create is True (registration flow):
            Creates Account with unique username, is_active=True, unusable password.
            Creates UserProfile, merges cart, and logs user in.
            Returns (user, True, None)
    """
    email = email.strip().lower()
    first_name = (first_name or "").strip()[:50]
    last_name = (last_name or "").strip()[:50]

    if not first_name:
        first_name = email.split("@")[0].capitalize()[:50]

    user = Account.objects.filter(email__iexact=email).first()

    if user:
        dirty = False
        if not user.is_active:
            user.is_active = True
            dirty = True
        if not user.first_name and first_name:
            user.first_name = first_name
            dirty = True
        if not user.last_name and last_name:
            user.last_name = last_name
            dirty = True
        if dirty:
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.profile_picture:
            profile.profile_picture = "default/default-user.png"
            profile.save()

        _merge_cart(request, user)
        auth.login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return user, False, None

    # User does NOT exist in Account table
    if not allow_create:
        error_msg = f"No account found with Google email ({email}). Please create an account first or sign up below."
        return None, False, error_msg

    # Registration flow: create new user
    username = _generate_unique_username(email, first_name, last_name)
    user = Account.objects.create(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        phone_number="",
        is_active=True,  # Google email is pre-verified
    )
    user.set_unusable_password()
    user.save()

    UserProfile.objects.create(
        user=user,
        profile_picture="default/default-user.png",
    )

    _merge_cart(request, user)
    auth.login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return user, True, None


def login(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            _merge_cart(request, user)
            auth.login(request, user)
            messages.success(request, "You are now logged in.")
            url = request.META.get("HTTP_REFERER")
            try:
                query = requests.utils.urlparse(url).query
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


def google_login(request):
    """
    Initiate Google OAuth2 flow.
    Supports action='login' (default, requires existing account) or
    action='register' (creates account if new).
    """
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")

    action = request.GET.get("action", "login")
    request.session["google_oauth_action"] = action

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        request.session["google_oauth_next"] = next_url

    if not client_id or not client_secret:
        if settings.DEBUG:
            return render(
                request,
                "accounts/google_setup_guide.html",
                {
                    "redirect_uri": request.build_absolute_uri(reverse("accounts:google_callback")),
                    "next_url": next_url,
                    "action": action,
                },
            )
        else:
            messages.error(request, "Google sign-in is not configured yet. Please use email and password.")
            return redirect("accounts:login")

    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state

    redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", "") or request.build_absolute_uri(reverse("accounts:google_callback"))

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(google_auth_url)


def google_callback(request):
    """
    Handle Google OAuth2 callback.
    Exchanges code for tokens, fetches userinfo.
    If action='login' and user does not exist: aborts with smart error message.
    If action='register' and user does not exist: creates account.
    """
    error = request.GET.get("error")
    if error:
        messages.info(request, "Google sign-in was cancelled.")
        return redirect("accounts:login")

    code = request.GET.get("code")
    state = request.GET.get("state")
    expected_state = request.session.pop("google_oauth_state", None)

    if not state or state != expected_state:
        messages.error(request, "Invalid authentication session. Please try again.")
        return redirect("accounts:login")

    if not code:
        messages.error(request, "Authorization code not provided by Google.")
        return redirect("accounts:login")

    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
    redirect_uri = getattr(settings, "GOOGLE_REDIRECT_URI", "") or request.build_absolute_uri(reverse("accounts:google_callback"))

    try:
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            messages.error(request, "Failed to authenticate with Google. Please check your credentials.")
            return redirect("accounts:login")

        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        user_info = userinfo_resp.json()
    except Exception as e:
        messages.error(request, f"Network error during Google authentication: {e}")
        return redirect("accounts:login")

    email = user_info.get("email")
    if not email:
        messages.error(request, "Could not retrieve email from your Google account.")
        return redirect("accounts:login")

    first_name = user_info.get("given_name") or ""
    last_name = user_info.get("family_name") or ""
    full_name = user_info.get("name") or ""

    if not first_name and full_name:
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        if len(parts) > 1:
            last_name = parts[1]

    picture_url = user_info.get("picture", "")

    action = request.session.pop("google_oauth_action", "login")
    allow_create = (action == "register")

    user, created, error_msg = _handle_google_user(
        request=request,
        email=email,
        first_name=first_name,
        last_name=last_name,
        picture_url=picture_url,
        allow_create=allow_create,
    )

    if error_msg:
        messages.error(request, error_msg)
        return redirect("accounts:login")

    if created:
        messages.success(request, f"Welcome to ChicCherry, {user.first_name}! Your account has been created.")
    else:
        messages.success(request, f"Welcome back, {user.first_name}!")

    next_url = request.session.pop("google_oauth_next", None)
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("accounts:dashboard")


@csrf_exempt
def google_one_tap(request):
    """
    Handle Google One Tap / Identity Services credential token (POST).
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    credential = request.POST.get("credential")
    action = request.POST.get("action", "login")

    if not credential:
        try:
            body = json.loads(request.body)
            credential = body.get("credential")
            action = body.get("action", action)
        except Exception:
            pass

    if not credential:
        return JsonResponse({"status": "error", "message": "Missing credential token"}, status=400)

    try:
        resp = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}",
            timeout=10,
        )
        info = resp.json()

        if "email" not in info:
            return JsonResponse({"status": "error", "message": "Invalid Google token"}, status=400)

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        if client_id and info.get("aud") != client_id:
            return JsonResponse({"status": "error", "message": "Audience mismatch"}, status=400)

        email = info.get("email")
        first_name = info.get("given_name") or ""
        last_name = info.get("family_name") or ""
        full_name = info.get("name") or ""
        if not first_name and full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            if len(parts) > 1:
                last_name = parts[1]

        allow_create = (action == "register")
        user, created, error_msg = _handle_google_user(
            request=request,
            email=email,
            first_name=first_name,
            last_name=last_name,
            picture_url=info.get("picture", ""),
            allow_create=allow_create,
        )

        if error_msg:
            return JsonResponse({"status": "error", "message": error_msg}, status=404)

        if created:
            messages.success(request, f"Welcome to ChicCherry, {user.first_name}! Your account has been created.")
        else:
            messages.success(request, f"Welcome, {user.first_name}!")

        next_url = request.session.pop("google_oauth_next", None) or reverse("accounts:dashboard")
        return JsonResponse({"status": "success", "redirect_url": next_url})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def google_dev_mock(request):
    """
    Development-only simulated Google login.
    Enables testing user verification and cart merging
    even before Google Cloud Console credentials are configured.
    """
    if not settings.DEBUG:
        messages.error(request, "Mock login is only available in development mode.")
        return redirect("accounts:login")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip() or "Google"
        last_name = request.POST.get("last_name", "").strip() or "User"
        action = request.POST.get("action", "login")

        if not email or "@" not in email:
            messages.error(request, "Please enter a valid Gmail / email address.")
            return redirect("accounts:google_login")

        allow_create = (action == "register")
        user, created, error_msg = _handle_google_user(
            request=request,
            email=email,
            first_name=first_name,
            last_name=last_name,
            allow_create=allow_create,
        )

        if error_msg:
            messages.error(request, error_msg)
            return redirect("accounts:login")

        if created:
            messages.success(request, f"[DEV DEMO] New account created for {user.email}!")
        else:
            messages.success(request, f"[DEV DEMO] Welcome back! Logged in with {user.email}.")

        next_url = request.session.pop("google_oauth_next", None)
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect("accounts:dashboard")

    return redirect("accounts:login")


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

    saved_payment_methods = PaymentAccount.objects.filter(user=request.user).order_by("-updated_at")

    context = {
        "orders_count": orders_count,
        "userprofile": userprofile,
        "saved_payment_methods": saved_payment_methods,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required(login_url="accounts:login")
def payment_methods(request):
    method_choices = [
        {
            "code": "bkash",
            "name": "bKash",
            "rule": "11 digits (e.g., 017XXXXXXXX)",
            "image": "paymentImg/images.jpg",
        },
        {
            "code": "rocket",
            "name": "Rocket",
            "rule": "10-16 digits",
            "image": "paymentImg/images.png",
        },
        {
            "code": "nogod",
            "name": "Nogod",
            "rule": "11 digits",
            "image": "paymentImg/নগদের_লোগো.png",
        },
        {
            "code": "upay",
            "name": "Upay",
            "rule": "11 digits",
            "image": "paymentImg/png-transparent-paypal-logo-paypal-logo-paypal-blue-text-trademark.png",
        },
        {
            "code": "visa",
            "name": "Visa",
            "rule": "13-16 digits",
            "image": "paymentImg/visa-new-2021-logo-png_seeklogo-408695.png",
        },
        {
            "code": "mastercard",
            "name": "Mastercard",
            "rule": "16 digits",
            "image": "paymentImg/American-Express-Logo-Download-Free-PNG.png",
        },
    ]
    method_names = {m["code"]: m["name"] for m in method_choices}

    if request.method == "POST":
        method = request.POST.get("payment_method", "").strip().lower()
        account_number = request.POST.get("account_number", "").strip()

        if method not in method_names:
            messages.error(request, "Please choose a valid payment method.")
            return redirect("accounts:payment_methods")

        if not account_number or not validate_account_number(account_number, method):
            messages.error(
                request,
                f"Invalid account number for {method_names.get(method)}. Please check the required digits format.",
            )
            return redirect("accounts:payment_methods")

        account, created = PaymentAccount.objects.update_or_create(
            user=request.user,
            payment_method=method,
            defaults={"account_number": account_number},
        )
        action_word = "added" if created else "updated"
        messages.success(
            request, f"{method_names.get(method)} account {action_word} successfully!"
        )
        return redirect("accounts:payment_methods")

    saved_accounts = PaymentAccount.objects.filter(user=request.user).order_by("-updated_at")

    method_info_map = {m["code"]: m for m in method_choices}
    accounts_with_info = []
    for sa in saved_accounts:
        info = method_info_map.get(sa.payment_method, {})
        accounts_with_info.append(
            {
                "id": sa.id,
                "method_code": sa.payment_method,
                "method_name": info.get("name", sa.get_payment_method_display()),
                "masked_number": sa.masked_account_number(),
                "image": info.get("image", ""),
                "updated_at": sa.updated_at,
            }
        )

    context = {
        "saved_accounts": accounts_with_info,
        "method_choices": method_choices,
    }
    return render(request, "accounts/payment_methods.html", context)


@login_required(login_url="accounts:login")
def delete_payment_method(request, account_id):
    if request.method == "POST":
        try:
            account = PaymentAccount.objects.get(id=account_id, user=request.user)
            name = account.get_payment_method_display()
            account.delete()
            messages.success(request, f"{name} payment account removed successfully.")
        except PaymentAccount.DoesNotExist:
            messages.error(request, "Payment account not found.")
    return redirect("accounts:payment_methods")


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
