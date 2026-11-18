from django.conf import settings
from django.db import models
from django.utils import timezone


class ShortURL(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="short_urls",
    )
    short_code = models.CharField(max_length=32, unique=True)  # case-sensitive
    original_url = models.URLField(max_length=2048)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table='ShortURL'
        ordering = ["-created_at"]
        verbose_name = "short URL"
        verbose_name_plural = "short URLs"
        indexes = [
            models.Index(fields=["owner", "-created_at"], name="shorturl_owner_created_idx"),
        ]

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_expired
