from django.db import models
from category.models import Category
from django.urls import reverse
from accounts.models import Account
from django.db.models import Avg, Count

# Create your models here.

class Product(models.Model):
    product_name    = models.CharField(max_length=200, unique=True)
    slug            = models.SlugField(max_length=200, unique=True)
    description     = models.TextField(max_length=500, blank=True)
    price           = models.IntegerField()
    discount_percent = models.PositiveIntegerField(default=0, help_text='Discount percentage (0 = no discount)')
    images          = models.ImageField(upload_to='photos/products')
    stock           = models.IntegerField()
    is_available    = models.BooleanField(default=True)
    category        = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date    = models.DateTimeField(auto_now_add=True)
    modified_date   = models.DateTimeField(auto_now=True)

    @property
    def discounted_price(self):
        if self.discount_percent > 0:
            return int(self.price * (100 - self.discount_percent) / 100)
        return self.price

    def get_url(self):
        return reverse('product_detail_slug', args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

    def averageReview(self):
        reviews = ReviewRating.objects.filter(product=self, is_visible=True).aggregate(average=Avg('rating'))
        avg = 0
        if reviews['average'] is not None:
            avg = float(reviews['average'])
        return avg

    def countReview(self):
        reviews = ReviewRating.objects.filter(product=self, is_visible=True).aggregate(count=Count('id'))
        count = 0
        if reviews['count'] is not None:
            count = int(reviews['count'])
        return count

class VariationCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Variation Categories'


class VariationManager(models.Manager):
    def by_category(self, category_name):
        return super().filter(variation_category__name__iexact=category_name, is_active=True)


class Variation(models.Model):
    product            = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation_category = models.ForeignKey(VariationCategory, on_delete=models.CASCADE)
    variation_value    = models.CharField(max_length=100)
    is_active          = models.BooleanField(default=True)
    created_date       = models.DateTimeField(auto_now=True)

    objects = VariationManager()

    def __str__(self):
        return self.variation_value


class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField()
    ip = models.CharField(max_length=20, blank=True)
    is_visible = models.BooleanField(default=False)  # Changed from status, requires moderation
    purchase_verified = models.BooleanField(default=False)
    image = models.ImageField(upload_to='reviews/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject


class ReviewAudit(models.Model):
    review = models.ForeignKey(ReviewRating, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # e.g., 'approved', 'rejected', 'edited'
    performed_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.review} by {self.performed_by}"


class HelpfulnessVote(models.Model):
    review = models.ForeignKey(ReviewRating, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    is_helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'user')

    def __str__(self):
        return f"{self.user} voted {'helpful' if self.is_helpful else 'not helpful'} on {self.review}"


class FooterSettings(models.Model):
    logo_text    = models.CharField(max_length=100, default='ChicCherry')
    header_email = models.EmailField(default='ChicCherry@gmail.com')
    header_phone = models.CharField(max_length=30, default='+8801701020304')
    email        = models.EmailField(default='ChicCherry@gmail.com')
    phone        = models.CharField(max_length=30, default='+8801701020304')
    address      = models.CharField(max_length=200, default='Sylhet, Bangladesh')
    copy         = models.CharField(max_length=200, default='© 2025 ChicCherry')
    show_visa    = models.BooleanField(default=True)
    show_paypal  = models.BooleanField(default=True)
    show_master  = models.BooleanField(default=True)
    show_amex    = models.BooleanField(default=False)
    show_stripe  = models.BooleanField(default=False)

    class Meta:
        verbose_name = verbose_name_plural = 'Footer Settings'

    def __str__(self):
        return 'Footer Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class PaymentMethod(models.Model):
    name = models.CharField(max_length=50)
    icon_class = models.CharField(max_length=100, help_text='FontAwesome class (e.g., fab fa-cc-discover)')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class SliderItem(models.Model):
    MEDIA_TYPE_CHOICES = [('image', 'Image'), ('video', 'Video')]
    media_type   = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    image        = models.ImageField(upload_to='slider/', blank=True, null=True)
    video        = models.FileField(upload_to='slider/', blank=True, null=True)
    caption      = models.CharField(max_length=200, blank=True)
    duration     = models.PositiveIntegerField(default=4000, help_text='Duration in ms for images (ignored for videos)')
    order        = models.PositiveIntegerField(default=0)
    is_active    = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.media_type} slide #{self.order} — {self.caption or 'no caption'}"


class ProductGallery(models.Model):
    product = models.ForeignKey(Product, default=None, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='store/products', max_length=255)

    def __str__(self):
        return self.product.product_name

    class Meta:
        verbose_name = 'productgallery'
        verbose_name_plural = 'product gallery'
