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

urlpatterns = [
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
