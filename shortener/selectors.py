import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import ShortURL
from .utils import cache_key

logger = logging.getLogger(__name__)


def get_user_urls(*, owner) -> QuerySet[ShortURL]:
    return ShortURL.objects.filter(owner=owner)


def resolve_short_code(short_code: str) -> str | None:
    """
    Return the destination URL for an active, unexpired short code, else None.
    Hot path: Redis first, database on miss. Cache failures never break redirects.
    """
    key = cache_key(short_code)

    try:
        cached = cache.get(key)
    except Exception:
        logger.warning("Cache read failed for %s", key, exc_info=True)
        cached = None
    if cached:
        return cached

    now = timezone.now()
    row = (
        ShortURL.objects.filter(short_code=short_code, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .values("original_url", "expires_at")
        .first()
    )
    if row is None:
        return None  # misses are not cached so new codes work immediately

    ttl = settings.SHORT_URL_CACHE_TTL
    if row["expires_at"]:
        ttl = min(ttl, int((row["expires_at"] - now).total_seconds()))

    if ttl > 0:
        try:
            cache.set(key, row["original_url"], timeout=ttl)
        except Exception:
            logger.warning("Cache write failed for %s", key, exc_info=True)

    return row["original_url"]
