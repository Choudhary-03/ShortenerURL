from django.db import models
from django.utils import timezone


class Click(models.Model):
    class DeviceType(models.TextChoices):
        DESKTOP = "desktop", "Desktop"
        MOBILE = "mobile", "Mobile"
        TABLET = "tablet", "Tablet"
        BOT = "bot", "Bot"
        OTHER = "other", "Other"

    short_url = models.ForeignKey(
        "shortener.ShortURL", on_delete=models.CASCADE, related_name="clicks"
    )
    clicked_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # anonymized by default
    user_agent = models.TextField(blank=True)
    referrer = models.TextField(blank=True)
    referrer_domain = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=2, blank=True)
    device_type = models.CharField(
        max_length=20, choices=DeviceType.choices, default=DeviceType.OTHER
    )
    browser = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table='analytics'
        ordering = ["-clicked_at"]
        indexes = [
            models.Index(fields=["short_url", "-clicked_at"], name="click_url_time_idx"),
            models.Index(fields=["clicked_at"], name="click_time_idx"),
        ]

    def __str__(self):
        local_time = timezone.localtime(self.clicked_at)
        return f"Click on {self.short_url_id} at {local_time:%Y-%m-%d %I:%M:%S %p}"
