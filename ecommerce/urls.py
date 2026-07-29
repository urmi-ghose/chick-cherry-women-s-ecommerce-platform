"""ecommerce URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
import os
from . import views
from greatkart.admin_site import ChicCherryAdminSite

# Patch default admin site — preserves all existing model registrations
admin.site.__class__ = ChicCherryAdminSite
admin.site.logout_template = "accounts/logged_out.html"

from . import urls_admin
from django.shortcuts import redirect

urlpatterns = [
    path("secureadmin/manage-website/", urls_admin.admin_manage_website, name="admin_manage_website"),
    path("secureadmin/users/", urls_admin.admin_users_list, name="admin_users_list"),
    path("secureadmin/store/product/list/", urls_admin.admin_product_list, name="admin_product_list"),
    path("secureadmin/store/product/", lambda request: redirect("/secureadmin/store/product/list/")),
    path("secureadmin/category/list/", urls_admin.admin_category_list, name="admin_category_list"),
    path("secureadmin/orders/", urls_admin.admin_order_list, name="admin_order_list"),
    path("secureadmin/carts/order/", urls_admin.admin_order_list),
    path("secureadmin/carts/order/<int:pk>/change/", urls_admin.admin_order_change, name="admin_order_change_custom"),
    path("secureadmin/reviews/", urls_admin.admin_review_list, name="admin_review_list"),
    path("secureadmin/store/reviewrating/", urls_admin.admin_review_list),
    path("secureadmin/reviews/<int:pk>/approve/", urls_admin.admin_review_toggle, {'action': 'approve'}, name="admin_review_approve"),
    path("secureadmin/reviews/<int:pk>/reject/",  urls_admin.admin_review_toggle, {'action': 'reject'},  name="admin_review_reject"),
    path("secureadmin/store-preview/", urls_admin.admin_store_preview, name="admin_store_preview"),
    path("secureadmin/discounts/", urls_admin.admin_discount_products, name="admin_discount_products"),
    path("secureadmin/accounts/", lambda request: redirect("/secureadmin/accounts/account/")),

    path("secureadmin/", admin.site.urls),
    path("", views.home, name="home"),
    path("store/", include("store.urls")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("cart/", include("carts.urls", namespace="carts")),
    path(
        "product-detail/<int:product_id>/", views.product_detail, name="product_detail"
    ),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(
        "/photos/", document_root=os.path.join(settings.BASE_DIR, "media", "photos")
    )
