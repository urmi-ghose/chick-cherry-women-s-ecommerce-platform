from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, OrderStatusUpdate
from email_utils import send_email_via_nodemailer
from django.conf import settings
from django.utils import timezone

# Register your models here.


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderStatusUpdateInline(admin.TabularInline):
    model = OrderStatusUpdate
    readonly_fields = ("timestamp", "updated_by")
    extra = 0



class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "full_name",
        "email",
        "status",
        "payment_status",
        "created_at",
    )
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("order_number", "first_name", "last_name", "email")
    fields = ("status", "payment_status")
    inlines = [OrderStatusUpdateInline]

    def save_formset(self, request, form, formset, change):
        if formset.model == OrderStatusUpdate:
            instances = formset.save(commit=False)
            for instance in instances:
                is_new = instance.pk is None
                if getattr(instance, 'updated_by_id', None) is None:
                    instance.updated_by = request.user
                instance.save()

                if is_new:
                    # Update the order's status to match the status update
                    order = instance.order
                    order.status = instance.status
                    order.save(update_fields=['status'])

                    # Send notification email when status is updated
                    order_items = OrderItem.objects.filter(order=order)
                    items_list = "\n".join(
                        [
                            f"{item.product.product_name} - Quantity: {item.quantity} - Price: ${item.product_price}"
                            for item in order_items
                        ]
                    )

                    subject = "Order Status Update"
                    message = f"""Order Status Update
Your order status has been updated!

Order Number: {order.order_number}

Status: {instance.status}

Total Amount: ${order.order_total}

Order Items:
{items_list}
Shipping Address:
{order.first_name} {order.last_name}

{order.address_line_1}
{order.address_line_2}

{order.city}, {order.state}, {order.country}

Phone: {order.phone}

Email: {order.email}
"""
                    send_email_via_nodemailer(
                        to_email=order.email,
                        subject=subject,
                        html_content=None,
                        text_content=message,
                    )
            for obj in formset.deleted_objects:
                obj.delete()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data:
            # Create status update record
            OrderStatusUpdate.objects.create(
                order=obj, status=obj.status, updated_by=request.user
            )

            # Send notification email when status is updated
            order_items = OrderItem.objects.filter(order=obj)
            items_list = "\n".join(
                [
                    f"{item.product.product_name} - Quantity: {item.quantity} - Price: ${item.product_price}"
                    for item in order_items
                ]
            )

            subject = "Order Status Update"
            message = f"""Order Status Update
Your order status has been updated!

Order Number: {obj.order_number}

Status: {obj.status}

Total Amount: ${obj.order_total}

Order Items:
{items_list}
Shipping Address:
{obj.first_name} {obj.last_name}

{obj.address_line_1}
{obj.address_line_2}

{obj.city}, {obj.state}, {obj.country}

Phone: {obj.phone}

Email: {obj.email}
"""
            send_email_via_nodemailer(to_email=obj.email, subject=subject, html_content=None, text_content=message)
        super().save_model(request, obj, form, change)


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(OrderStatusUpdate)
