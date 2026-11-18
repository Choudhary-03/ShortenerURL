from django.contrib import admin

from .models import Click


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ("short_url", "clicked_at", "device_type", "browser", "country", "referrer_domain")
    list_filter = ("device_type", "country", "clicked_at")
    search_fields = ("short_url__short_code", "referrer_domain")
    raw_id_fields = ("short_url",)
    date_hierarchy = "clicked_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # click events are immutable
