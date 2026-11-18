from django.contrib import admin

from .models import ShortURL


@admin.register(ShortURL)
class ShortURLAdmin(admin.ModelAdmin):
    list_display = ("short_code", "original_url", "owner", "is_active", "expires_at", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("short_code", "original_url", "owner__email")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("owner",)
    ordering = ("-created_at",)
