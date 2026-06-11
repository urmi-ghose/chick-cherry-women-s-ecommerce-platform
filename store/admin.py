from django.contrib import admin
from .models import Product, Variation, VariationCategory, ReviewRating, ReviewAudit, HelpfulnessVote, ProductGallery
from django.contrib import messages
from django.utils.html import format_html


class VariationInline(admin.TabularInline):
    model = Variation
    extra = 1


class ReviewAuditInline(admin.TabularInline):
    model = ReviewAudit
    readonly_fields = ('action', 'performed_by', 'timestamp', 'notes')
    extra = 0
    can_delete = False


class ReviewRatingAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'product', 'rating', 'is_visible', 'purchase_verified', 'created_at')
    list_filter = ('is_visible', 'purchase_verified', 'rating', 'created_at')
    search_fields = ('subject', 'review', 'user__email', 'product__product_name')
    readonly_fields = ('user', 'product', 'subject', 'review', 'rating', 'ip', 'purchase_verified', 'created_at', 'updated_at')
    list_editable = ('is_visible',)
    actions = ['approve_reviews', 'reject_reviews']
    inlines = [ReviewAuditInline]

    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_visible=True)
        for review in queryset:
            ReviewAudit.objects.create(
                review=review,
                action='approved',
                performed_by=request.user,
                notes='Approved via admin action'
            )
        self.message_user(request, f'{updated} reviews approved and made visible.')
    approve_reviews.short_description = "Approve selected reviews"

    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_visible=False)
        for review in queryset:
            ReviewAudit.objects.create(
                review=review,
                action='rejected',
                performed_by=request.user,
                notes='Rejected via admin action'
            )
        self.message_user(request, f'{updated} reviews rejected and hidden.')
    reject_reviews.short_description = "Reject selected reviews"


class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 1
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;border-radius:6px;object-fit:cover;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'discount_percent', 'stock', 'category', 'modified_date', 'is_available')
    def get_prepopulated_fields(self, request, obj=None):
        return {} if obj else {'slug': ('product_name',)}
    fieldsets = (
        (None, {'fields': ('product_name', 'description', 'category', 'images', 'stock', 'is_available')}),
        ('Pricing', {'fields': ('price', 'discount_percent')}),
    )

    inlines = [VariationInline, ProductGalleryInline]

    def get_fieldsets(self, request, obj=None):
        if not obj:  # adding new product — include slug
            return (
                (None, {'fields': ('product_name', 'slug', 'description', 'category', 'images', 'stock', 'is_available')}),
                ('Pricing', {'fields': ('price', 'discount_percent')}),
            )
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing existing product
            return ('slug',)
        return ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'discount_percent' in form.base_fields:
            form.base_fields['discount_percent'].widget.attrs.update({'class': '', 'min': 0, 'max': 100})
        return form

    def save_model(self, request, obj, form, change):
        print(f"[DEBUG save_model] POST data: {dict(request.POST)}")
        print(f"[DEBUG save_model] form.is_valid={form.is_valid()} errors={form.errors}")
        print(f"[DEBUG save_model] discount_percent={obj.discount_percent}")
        super().save_model(request, obj, form, change)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST':
            print(f"[DEBUG changeform_view] POST={dict(request.POST)}")
        response = super().changeform_view(request, object_id, form_url, extra_context)
        if request.method == 'POST':
            from django.http import HttpResponseRedirect
            if not isinstance(response, HttpResponseRedirect):
                ctx = getattr(response, 'context_data', None)
                if ctx:
                    if 'adminform' in ctx:
                        print(f"[DEBUG] main form errors: {ctx['adminform'].form.errors}")
                        print(f"[DEBUG] non-field errors: {ctx['adminform'].form.non_field_errors()}")
                    for fs in ctx.get('inline_admin_formsets', []):
                        for i, f in enumerate(fs.formset.forms):
                            if f.errors:
                                print(f"[DEBUG] inline {fs.opts.verbose_name} form[{i}] errors: {f.errors}")
                        if fs.formset.non_form_errors():
                            print(f"[DEBUG] inline {fs.opts.verbose_name} non_form_errors: {fs.formset.non_form_errors()}")
        return response


admin.site.register(Product, ProductAdmin)
admin.site.register(VariationCategory)
admin.site.register(ReviewRating, ReviewRatingAdmin)
admin.site.register(ReviewAudit)
admin.site.register(HelpfulnessVote)
