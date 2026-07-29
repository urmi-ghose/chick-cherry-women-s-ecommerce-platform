from .models import CartItem
from .views import _cart_id


def counter(request):
    """
    Context processor to count cart items for the current session.
    """
    cart_count = 0
    if "admin" in request.path:
        return {}
    else:
        try:
            cart = CartItem.objects.filter(cart__cart_id=_cart_id(request))
            for cart_item in cart:
                cart_count += cart_item.quantity
        except CartItem.DoesNotExist:
            cart_count = 0
    return dict(cart_count=cart_count)
