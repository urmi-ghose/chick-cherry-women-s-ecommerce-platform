from django.shortcuts import render
from store.models import Product, ReviewRating
from django.conf import settings


def home(request):
    products = Product.objects.all().filter(is_available=True).order_by("created_date")

    # Get the reviews
    reviews = None
    for product in products:
        reviews = ReviewRating.objects.filter(product_id=product.id, is_visible=True)

    context = {
        "products": products,
        "reviews": reviews,
        "USE_MINIO": getattr(settings, "USE_MINIO", False),
        "MINIO_ENDPOINT": getattr(settings, "MINIO_ENDPOINT", "localhost:9000"),
        "MINIO_BUCKET_NAME": getattr(settings, "MINIO_BUCKET_NAME", "greatkart-media"),
    }
    return render(request, "home.html", context)
