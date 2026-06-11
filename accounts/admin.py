from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account, UserProfile
from django.utils.html import format_html

# Register your models here.

admin.site.site_header = "Admin Panel"


class AccountAdmin(UserAdmin):
    # show primary key so admin ordering can match DB viewers
    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "username",
        "last_login",
        "date_joined",
        "is_active",
        "is_staff",
        "is_admin",
        "is_superadmin",
    )
    list_display_links = ("email", "first_name", "last_name")
    list_editable = ("is_active", "is_staff", "is_admin", "is_superadmin")
    readonly_fields = (
        "first_name",
        "last_name",
        "username",
        "email",
        "phone_number",
        "last_login",
        "date_joined",
    )
    # default DB viewers typically show rows by id ascending; set admin to match
    ordering = ("id",)

    filter_horizontal = ()
    list_filter = ()
    fieldsets = (
        (
            "Personal Info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "email",
                    "phone_number",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_admin", "is_superadmin")},
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )
    actions = ["delete_selected"]


class UserProfileAdmin(admin.ModelAdmin):
    def thumbnail(self, object):
        return format_html(
            '<img src="{}" width="30" style="border-radius:50%;">'.format(
                object.profile_picture.url
            )
        )

    thumbnail.short_description = "Profile Picture"
    list_display = ("thumbnail", "user", "city", "state", "country")


admin.site.register(Account, AccountAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
