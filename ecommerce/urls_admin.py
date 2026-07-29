from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect, render
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from urllib.parse import urlencode
import os
from greatkart.admin_site import ChicCherryAdminSite

admin.site.__class__ = ChicCherryAdminSite
admin.site.logout_template = "accounts/logged_out.html"


@staff_member_required(login_url="/secureadmin/login/")
def admin_users_list(request):
    from accounts.models import Account
    from django.utils import timezone
    from datetime import timedelta

    keyword     = request.GET.get('keyword', '')
    filter_tab  = request.GET.get('filter', '')
    sort        = request.GET.get('sort', '')

    base_qs = Account.objects.filter(is_staff=False, is_admin=False, is_superadmin=False)

    # stat counts (always on full base)
    total_count    = base_qs.count()
    active_count   = base_qs.filter(is_active=True).count()
    inactive_count = base_qs.filter(is_active=False).count()
    month_start    = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = base_qs.filter(date_joined__gte=month_start).count()

    users = base_qs
    if keyword:
        users = users.filter(
            Q(first_name__icontains=keyword) |
            Q(last_name__icontains=keyword) |
            Q(email__icontains=keyword)
        )
    if filter_tab == 'active':
        users = users.filter(is_active=True)
    elif filter_tab == 'inactive':
        users = users.filter(is_active=False)
    elif filter_tab == 'new':
        users = users.filter(date_joined__gte=month_start)

    sort_map = {
        'joined':     '-date_joined',
        'joined_asc': 'date_joined',
        'login':      '-last_login',
        'login_asc':  'last_login',
    }
    users = users.order_by(sort_map.get(sort, '-date_joined'))

    paginator  = Paginator(users, 20)
    paged_users = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/users_list.html', {
        'users':          paged_users,
        'user_count':     total_count,
        'total_count':    total_count,
        'active_count':   active_count,
        'inactive_count': inactive_count,
        'new_this_month': new_this_month,
        'keyword':        keyword,
    })


@staff_member_required(login_url="/secureadmin/login/")
def admin_order_change(request, pk):
    from carts.models import Order, OrderItem, OrderStatusUpdate
    from django.contrib.admin import site
    order = Order.objects.filter(pk=pk).first()
    if not order:
        from django.http import Http404
        raise Http404
    order_items    = OrderItem.objects.filter(order=order).prefetch_related('variations', 'product')
    status_history = OrderStatusUpdate.objects.filter(order=order).order_by('-timestamp')
    from carts.models import PaymentAccount
    payment_account = PaymentAccount.objects.filter(user=order.user).first() if order.user else None
    model_admin    = site._registry.get(Order)
    extra = {'order_items': order_items, 'status_history': status_history, 'payment_account': payment_account}
    return model_admin.change_view(request, str(pk), extra_context=extra)


@staff_member_required(login_url="/secureadmin/login/")
def admin_review_list(request):
    from store.models import ReviewRating, ReviewAudit
    from django.db.models import Q

    keyword        = request.GET.get('q', '')
    current_filter = request.GET.get('filter', '')

    reviews = ReviewRating.objects.select_related('user', 'product').order_by('-created_at')
    if keyword:
        reviews = reviews.filter(
            Q(subject__icontains=keyword) |
            Q(review__icontains=keyword) |
            Q(user__email__icontains=keyword) |
            Q(product__product_name__icontains=keyword)
        )
    if current_filter == 'visible':  reviews = reviews.filter(is_visible=True)
    elif current_filter == 'hidden': reviews = reviews.filter(is_visible=False)
    elif current_filter == 'verified': reviews = reviews.filter(purchase_verified=True)

    base = ReviewRating.objects
    total_count    = base.count()
    visible_count  = base.filter(is_visible=True).count()
    hidden_count   = base.filter(is_visible=False).count()
    verified_count = base.filter(purchase_verified=True).count()

    paginator = Paginator(reviews, 6)
    paged     = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/store/reviewrating/change_list.html', {
        'reviews':        paged,
        'keyword':        keyword,
        'current_filter': current_filter,
        'total_count':    total_count,
        'visible_count':  visible_count,
        'hidden_count':   hidden_count,
        'verified_count': verified_count,
        'has_permission': True,
    })


@staff_member_required(login_url="/secureadmin/login/")
def admin_review_toggle(request, pk, action):
    from store.models import ReviewRating, ReviewAudit
    review = ReviewRating.objects.filter(pk=pk).first()
    if review and request.method == 'POST':
        review.is_visible = (action == 'approve')
        review.save()
        ReviewAudit.objects.create(
            review=review,
            action='approved' if action == 'approve' else 'rejected',
            performed_by=request.user,
            notes=f'Quick {action} from reviews list'
        )
    return redirect('/secureadmin/reviews/')


@staff_member_required(login_url="/secureadmin/login/")
def admin_order_list(request):
    from carts.models import Order
    from django.db.models import Sum, Count

    keyword = request.GET.get('q', '')
    status  = request.GET.get('status', '')
    payment = request.GET.get('payment', '')
    sort    = request.GET.get('sort', '')

    orders = Order.objects.all()
    if keyword:
        orders = orders.filter(
            Q(order_number__icontains=keyword) |
            Q(first_name__icontains=keyword) |
            Q(last_name__icontains=keyword) |
            Q(email__icontains=keyword)
        )
    if status:  orders = orders.filter(status=status)
    if payment: orders = orders.filter(payment_status=payment)

    sort_map = {
        'num':      'order_number', 'num_asc':  '-order_number',
        'date':     'created_at',   'date_asc': '-created_at',
    }
    orders = orders.order_by(sort_map.get(sort, '-created_at'))

    # stats
    base = Order.objects
    total_orders      = base.count()
    pending_orders    = base.filter(status__in=['Placed','New']).count()
    processing_orders = base.filter(status__in=['Processing','Shipped']).count()
    delivered_orders  = base.filter(status__in=['Delivered','Completed']).count()
    total_revenue     = round(base.aggregate(t=Sum('order_total'))['t'] or 0)

    # tab counts
    status_tabs = [
        {'label': 'All',        'value': '',           'count': base.count()},
        {'label': 'Placed',     'value': 'Placed',     'count': base.filter(status='Placed').count()},
        {'label': 'Processing', 'value': 'Processing', 'count': base.filter(status='Processing').count()},
        {'label': 'Shipped',    'value': 'Shipped',    'count': base.filter(status='Shipped').count()},
        {'label': 'Delivered',  'value': 'Delivered',  'count': base.filter(status='Delivered').count()},
        {'label': 'Cancelled',  'value': 'Cancelled',  'count': base.filter(status='Cancelled').count()},
    ]

    paginator = Paginator(orders, 15)
    paged     = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/carts/order/change_list.html', {
        'orders':             paged,
        'keyword':            keyword,
        'current_status':     status,
        'total_orders':       total_orders,
        'pending_orders':     pending_orders,
        'processing_orders':  processing_orders,
        'delivered_orders':   delivered_orders,
        'total_revenue':      f"{total_revenue:,}",
        'status_tabs':        status_tabs,
        'has_permission':     True,
    })


@staff_member_required(login_url="/secureadmin/login/")
def admin_category_list(request):
    from category.models import Category
    from store.models import Product
    from django.db.models import Count

    q = request.GET.get('q', '')
    categories = Category.objects.annotate(product_count=Count('product')).order_by('category_name')
    if q:
        categories = categories.filter(category_name__icontains=q)

    total_count      = Category.objects.count()
    with_image_count = Category.objects.exclude(cat_image='').count()
    total_products   = Product.objects.count()

    paginator  = Paginator(categories, 8)
    paged      = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/category/category/change_list.html', {
        'categories':       paged,
        'total_count':      total_count,
        'with_image_count': with_image_count,
        'total_products':   total_products,
        'has_permission':   True,
    })


@staff_member_required(login_url="/secureadmin/login/")
def admin_product_list(request):
    from store.models import Product
    from category.models import Category

    q     = request.GET.get('q', '')
    cat   = request.GET.get('cat', '')
    avail = request.GET.get('avail', '')

    products = Product.objects.select_related('category').order_by('-modified_date')
    if q:
        products = products.filter(product_name__icontains=q)
    if cat:
        products = products.filter(category__id=cat)
    if avail == '1':
        products = products.filter(is_available=True)
    elif avail == '0':
        products = products.filter(is_available=False)

    total_count     = Product.objects.count()
    available_count = Product.objects.filter(is_available=True).count()
    discount_count  = Product.objects.filter(discount_percent__gt=0).count()
    low_stock_count = Product.objects.filter(stock__lte=5, stock__gt=0).count()

    paginator      = Paginator(products, 8)
    paged          = paginator.get_page(request.GET.get('page'))
    all_categories = Category.objects.all()

    return render(request, 'admin/store/product/change_list.html', {
        'products':        paged,
        'all_categories':  all_categories,
        'total_count':     total_count,
        'available_count': available_count,
        'discount_count':  discount_count,
        'low_stock_count': low_stock_count,
        'has_permission':  True,
    })


@staff_member_required(login_url="/secureadmin/login/")
def admin_store_preview(request):
    from store.models import Product, Variation
    from category.models import Category

    keyword   = request.GET.get('keyword')
    sizes     = request.GET.getlist('size')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    available_sizes = Variation.objects.filter(
        variation_category__name__iexact='size', is_active=True
    ).values_list('variation_value', flat=True).distinct()

    products = Product.objects.filter(is_available=True).order_by('id')

    if keyword:
        products = products.filter(Q(product_name__icontains=keyword))
    if sizes:
        products = products.filter(
            variation__variation_category__name__iexact='size',
            variation__variation_value__in=sizes,
            variation__is_active=True
        ).distinct()
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    paginator      = Paginator(products, 9)
    paged_products = paginator.get_page(request.GET.get('page'))
    product_count  = products.count()

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    params = urlencode(query_params)

    return render(request, 'admin/store_preview.html', {
        'products':        paged_products,
        'product_count':   product_count,
        'available_sizes': available_sizes,
        'keyword':         keyword,
        'sizes':           sizes,
        'min_price':       min_price,
        'max_price':       max_price,
        'params':          params,
    })


@staff_member_required(login_url="/secureadmin/login/")
def admin_discount_products(request):
    from store.models import Product

    keyword   = request.GET.get('keyword', '')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    products = Product.objects.filter(is_available=True, discount_percent__gt=0).order_by('-discount_percent')

    if keyword:
        products = products.filter(Q(product_name__icontains=keyword))

    # Filter by discounted price in Python
    products = list(products)
    if min_price:
        products = [p for p in products if p.discounted_price >= int(min_price)]
    if max_price:
        products = [p for p in products if p.discounted_price <= int(max_price)]

    product_count = len(products)
    paginator = Paginator(products, 6)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    params = urlencode(query_params)

    return render(request, 'admin/discount_products.html', {
        'products':      paged_products,
        'product_count': product_count,
        'keyword':       keyword,
        'min_price':     min_price,
        'max_price':     max_price,
        'params':        params,
    })


@staff_member_required(login_url="/secureadmin/login/")
def admin_manage_website(request):
    from store.models import FooterSettings, PaymentMethod, SliderItem
    from django.contrib import messages
    footer = FooterSettings.get()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_payment':
            name = request.POST.get('pm_name', '').strip()
            icon = request.POST.get('pm_icon', '').strip()
            if name and icon:
                PaymentMethod.objects.create(name=name, icon_class=icon)
                messages.success(request, f'Payment method "{name}" added!')
            else:
                messages.error(request, 'Name and icon class are required.')
        elif action == 'delete_payment':
            pm_id = request.POST.get('pm_id')
            PaymentMethod.objects.filter(pk=pm_id).delete()
            messages.success(request, 'Payment method removed.')
        elif action == 'add_slider':
            media_type = request.POST.get('slider_media_type', 'image')
            caption    = request.POST.get('slider_caption', '').strip()
            duration   = int(request.POST.get('slider_duration') or 4000)
            order      = int(request.POST.get('slider_order') or 0)
            item = SliderItem(media_type=media_type, caption=caption, duration=duration, order=order)
            if media_type == 'image' and 'slider_image' in request.FILES:
                item.image = request.FILES['slider_image']
            elif media_type == 'video' and 'slider_video' in request.FILES:
                item.video = request.FILES['slider_video']
            else:
                messages.error(request, 'Please upload a file for the slider.')
                return redirect(request.path)
            item.save()
            messages.success(request, 'Slider item added!')
        elif action == 'edit_slider':
            item = SliderItem.objects.filter(pk=request.POST.get('slider_id')).first()
            if item:
                item.caption  = request.POST.get('slider_caption', '').strip()
                item.duration = int(request.POST.get('slider_duration') or 4000)
                item.order    = int(request.POST.get('slider_order') or 0)
                media_type    = request.POST.get('slider_media_type', item.media_type)
                item.media_type = media_type
                if media_type == 'image' and 'slider_image' in request.FILES:
                    item.image = request.FILES['slider_image']
                    item.video = None
                elif media_type == 'video' and 'slider_video' in request.FILES:
                    item.video = request.FILES['slider_video']
                    item.image = None
                item.save()
                messages.success(request, 'Slider item updated!')
        elif action == 'delete_slider':
            SliderItem.objects.filter(pk=request.POST.get('slider_id')).delete()
            messages.success(request, 'Slider item removed.')
        elif action == 'toggle_slider':
            item = SliderItem.objects.filter(pk=request.POST.get('slider_id')).first()
            if item:
                item.is_active = not item.is_active
                item.save()
        else:
            footer.email      = request.POST.get('footer_email', footer.email)
            footer.phone      = request.POST.get('footer_phone', footer.phone)
            footer.address    = request.POST.get('footer_address', footer.address)
            footer.copy       = request.POST.get('footer_copy', footer.copy)
            footer.logo_text    = request.POST.get('logo_text', footer.logo_text)
            footer.header_email = request.POST.get('header_email', footer.header_email)
            footer.header_phone = request.POST.get('header_phone', footer.header_phone)
            footer.show_visa   = 'show_visa'   in request.POST
            footer.show_paypal = 'show_paypal' in request.POST
            footer.show_master = 'show_master' in request.POST
            footer.show_amex   = 'show_amex'   in request.POST
            footer.show_stripe = 'show_stripe' in request.POST
            footer.save()
            messages.success(request, 'Footer settings saved successfully!')
        return redirect(request.path)
    return render(request, 'admin/manage_website.html', {
        'footer': footer,
        'payment_methods': PaymentMethod.objects.all(),
        'slider_items': SliderItem.objects.all(),
    })


urlpatterns = [
    path("", lambda request: redirect("secureadmin/")),
    path("secureadmin/manage-website/", admin_manage_website, name="admin_manage_website"),
    path("secureadmin/users/", admin_users_list, name="admin_users_list"),
    path("secureadmin/store/product/list/", admin_product_list, name="admin_product_list"),
    path("secureadmin/store/product/", lambda request: redirect("/secureadmin/store/product/list/")),
    path("secureadmin/category/list/", admin_category_list, name="admin_category_list"),
    path("secureadmin/orders/", admin_order_list, name="admin_order_list"),
    path("secureadmin/carts/order/", admin_order_list),
    path("secureadmin/carts/order/<int:pk>/change/", admin_order_change, name="admin_order_change_custom"),
    path("secureadmin/reviews/", admin_review_list, name="admin_review_list"),
    path("secureadmin/store/reviewrating/", admin_review_list),
    path("secureadmin/reviews/<int:pk>/approve/", admin_review_toggle, {'action': 'approve'}, name="admin_review_approve"),
    path("secureadmin/reviews/<int:pk>/reject/",  admin_review_toggle, {'action': 'reject'},  name="admin_review_reject"),
    path("secureadmin/store-preview/", admin_store_preview, name="admin_store_preview"),
    path("secureadmin/discounts/", admin_discount_products, name="admin_discount_products"),
    path("secureadmin/accounts/", lambda request: redirect("/secureadmin/accounts/account/")),
    path("secureadmin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static("/photos/", document_root=os.path.join(settings.BASE_DIR, "media", "photos"))
