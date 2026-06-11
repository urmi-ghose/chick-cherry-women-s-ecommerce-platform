import json
from django.contrib.admin import AdminSite
from django.db.models import Sum


class ChicCherryAdminSite(AdminSite):
    site_header = "ChicCherry"
    site_title  = "ChicCherry Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        from carts.models import Order
        from store.models import Product
        from accounts.models import Account
        from django.utils import timezone
        from django.db.models.functions import TruncMonth
        from datetime import timedelta

        order_count   = Order.objects.count()
        product_count = Product.objects.count()
        user_count    = Account.objects.filter(is_staff=False).count()
        revenue       = Order.objects.aggregate(t=Sum("order_total"))["t"] or 0

        recent = (
            Order.objects.order_by("-created_at")[:8]
            .values("id", "order_number", "first_name", "last_name",
                    "order_total", "status", "payment_status", "created_at")
        )
        recent_orders_json = json.dumps([
            {
                "id":           o["id"],
                "order_number": o["order_number"],
                "name":         f"{o['first_name']} {o['last_name']}",
                "total":        f"{o['order_total']:.0f}",
                "status":       o["status"],
                "payment":      o["payment_status"],
                "date":         o["created_at"].strftime("%b %d, %Y"),
            }
            for o in recent
        ])

        twelve_ago = timezone.now() - timedelta(days=365)
        monthly = (
            Order.objects
            .filter(created_at__gte=twelve_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("order_total"))
            .order_by("month")
        )
        chart_labels = [m["month"].strftime("%b %Y") for m in monthly]
        chart_data   = [round(m["total"] or 0, 2) for m in monthly]

        ctx = extra_context or {}
        ctx.update({
            "order_count":        order_count,
            "product_count":      product_count,
            "user_count":         user_count,
            "revenue":            f"{revenue:,.0f}",
            "recent_orders_json": recent_orders_json,
            "chart_labels_json":  json.dumps(chart_labels),
            "chart_data_json":    json.dumps(chart_data),
        })
        return super().index(request, extra_context=ctx)
