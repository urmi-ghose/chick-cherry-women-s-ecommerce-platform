from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
import os
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("store/", include("store.urls")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("cart/", include("carts.urls", namespace="carts")),
    path("product-detail/<int:product_id>/", views.product_detail, name="product_detail"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static("/photos/", document_root=os.path.join(settings.BASE_DIR, "media", "photos"))
