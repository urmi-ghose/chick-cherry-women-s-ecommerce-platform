from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating, ProductGallery, Variation
from category.models import Category
from carts.models import CartItem, Order, OrderItem
from django.db.models import Q

from carts.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from .forms import ReviewForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from urllib.parse import urlencode
from email_utils import send_email_via_nodemailer
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
# from orders.models import OrderProduct


def discount_products(request):
    products = Product.objects.filter(is_available=True, discount_percent__gt=0)
    
    # Search filter
    keyword = request.GET.get('keyword')
    if keyword:
        products = products.filter(Q(product_name__icontains=keyword))
    
    # Get min/max price from request
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    # Fetch all matching products first
    products = list(products.order_by('-discount_percent'))
    
    # Filter by discounted price in Python (since it's a property)
    if min_price:
        min_price = int(min_price)
        products = [p for p in products if p.discounted_price >= min_price]
    if max_price:
        max_price = int(max_price)
        products = [p for p in products if p.discounted_price <= max_price]
    
    # Pagination
    paginator = Paginator(products, 6)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    
    # Build query params for pagination
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    from urllib.parse import urlencode
    params = urlencode(query_params)
    
    context = {
        'products': paged_products,
        'product_count': len(products),
        'links': Category.objects.all(),
        'keyword': keyword,
        'min_price': min_price,
        'max_price': max_price,
        'params': params,
    }
    return render(request, 'store/discount_products.html', context)


def store(request, category_slug=None):
    categories = None
    products = None
    links = Category.objects.all()

    # Get filter parameters
    keyword = request.GET.get('keyword')
    sizes = request.GET.getlist('size')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Get available sizes dynamically
    available_sizes = Variation.objects.filter(variation_category__name__iexact='size', is_active=True).values_list('variation_value', flat=True).distinct()

    # Base queryset
    products = Product.objects.filter(is_available=True).order_by('id')

    # Filter by category if provided
    if category_slug is not None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=categories)

    # Filter by keyword
    if keyword:
        products = products.filter(Q(product_name__icontains=keyword))

    # Filter by sizes
    if sizes:
        products = products.filter(variation__variation_category__name__iexact='size', variation__variation_value__in=sizes, variation__is_active=True).distinct()

    # Filter by price
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Pagination
    paginator = Paginator(products, 3)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    product_count = products.count()

    # Build query params for pagination
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    params = urlencode(query_params)

    context = {
        'products': paged_products,
        'product_count': product_count,
        'links': links,
        'keyword': keyword,
        'sizes': sizes,
        'available_sizes': available_sizes,
        'min_price': min_price,
        'max_price': max_price,
        'params': params,
    }
    return render(request, 'store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        return redirect('store')
    except Exception as e:
        raise e

    # Get the reviews
    reviews = ReviewRating.objects.filter(product_id=single_product.id, is_visible=True)

    # Check if logged-in user has purchased and already reviewed
    has_purchased = False
    user_review = None
    if request.user.is_authenticated:
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product=single_product,
            order__status='Delivered'
        ).exists() or OrderItem.objects.filter(
            order__email=request.user.email,
            product=single_product,
            order__status='Delivered'
        ).exists()
        user_review = ReviewRating.objects.filter(user=request.user, product=single_product).first()

    # Get the product gallery
    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)

    # Get variations for color and size
    colors = single_product.variation_set.filter(variation_category__name__iexact='color', is_active=True)
    sizes = single_product.variation_set.filter(variation_category__name__iexact='size', is_active=True)

    context = {
        'single_product': single_product,
        'in_cart': in_cart,
        'reviews': reviews,
        'has_purchased': has_purchased,
        'user_review': user_review,
        'product_gallery': product_gallery,
        'colors': colors,
        'sizes': sizes,
    }
    return render(request, 'store/product_detail.html', context)


def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(product_name__icontains=keyword))
            product_count = products.count()

            # Pagination
            paginator = Paginator(products, 3)
            page = request.GET.get('page')
            paged_products = paginator.get_page(page)

            # Build query params for pagination
            query_params = request.GET.copy()
            if 'page' in query_params:
                del query_params['page']
            params = urlencode(query_params)

            context = {
                'products': paged_products,
                'product_count': product_count,
                'keyword': keyword,
                'params': params,
            }
        else:
            context = {
                'products': None,
                'product_count': 0,
                'keyword': keyword,
                'params': '',
            }
    else:
        context = {
            'products': None,
            'product_count': 0,
            'keyword': '',
            'params': '',
        }
    return render(request, 'store.html', context)


@login_required(login_url='accounts:login')
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    url = product.get_url()
    print(f"DEBUG REVIEW: product_id={product_id}, user={request.user.email}, redirect_url={url}")
    if request.method == 'POST':
        from django.utils import timezone
        from datetime import timedelta

        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product_id=product_id,
            order__status='Delivered'
        ).exists() or OrderItem.objects.filter(
            order__email=request.user.email,
            product_id=product_id,
            order__status='Delivered'
        ).exists()

        print(f"DEBUG REVIEW: has_purchased={has_purchased}")

        if not has_purchased:
            messages.error(request, 'You must have a Delivered order to review this product.')
            return redirect(url)

        form = ReviewForm(request.POST)
        if form.is_valid():
            data = form.save(commit=False)
            data.ip = request.META.get('REMOTE_ADDR')
            data.product_id = product_id
            data.user_id = request.user.id
            data.purchase_verified = True
            data.save()
            subject = f"Review Submitted for {data.product.product_name}"
            html_content = f"<h2>Thank you for your review!</h2><p>Your review for <strong>{data.product.product_name}</strong> has been submitted and is pending moderation.</p><p><strong>Rating:</strong> {data.rating} stars</p>"
            send_email_via_nodemailer(request.user.email, subject, html_content)
            messages.success(request, 'Thank you! Your review has been submitted and is pending approval.')
            return redirect(url)
        else:
            messages.error(request, 'Please correct the errors in your review form.')
            return redirect(url)


@login_required(login_url='accounts:login')
def submit_rating(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        from django.utils import timezone
        from datetime import timedelta
        # Rate limiting: check if user has submitted too many ratings recently
        recent_ratings = RatingSubmission.objects.filter(
            user=request.user,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()

        if recent_ratings >= 5:
            messages.error(request, 'You have submitted too many ratings recently. Please try again later.')
            return redirect(url)

        # Check if user has purchased the product (based on email in Order table)
        has_purchased = OrderItem.objects.filter(
            order__email=request.user.email,
            product_id=product_id,
            order__status__in=['Delivered', 'Shipped', 'Processing']
        ).exists()

        if not has_purchased:
            messages.error(request, 'You must purchase this product to submit a rating.')
            return redirect(url)

        form = RatingSubmissionForm(request.POST)
        if form.is_valid():
            data = form.save(commit=False)
            data.user = request.user
            data.product_id = product_id
            data.save()

            messages.success(request, 'Thank you! Your rating has been submitted.')
            return redirect(url)
        else:
            messages.error(request, 'Invalid rating submission.')
            return redirect(url)
    else:
        messages.error(request, 'Invalid request method.')
        return redirect(url)
