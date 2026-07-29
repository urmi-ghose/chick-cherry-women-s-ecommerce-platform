from carts.models import Cart, CartItem


def footer_settings(request):
    from store.models import FooterSettings, PaymentMethod
    return {
        'footer': FooterSettings.get(),
        'footer_payment_methods': PaymentMethod.objects.filter(is_active=True),
    }


def cart_counter(request):
    cart_count = 0
    if 'admin' in request.path:
        return {}
    else:
        try:
            if request.user.is_authenticated:
                cart_items = CartItem.objects.all().filter(user=request.user, is_active=True)
            else:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                cart_items = CartItem.objects.all().filter(cart=cart, is_active=True)
            for cart_item in cart_items:
                cart_count += cart_item.quantity
        except Cart.DoesNotExist:
            cart_count = 0
    return dict(cart_count=cart_count)


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart
