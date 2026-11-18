import logging

from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from .models import ShortURL
from .utils import cache_key, generate_code
from .validators import RESERVED_CODES

logger = logging.getLogger(__name__)

MAX_CODE_ATTEMPTS = 5
UPDATABLE_FIELDS = {"original_url", "is_active", "expires_at"}


class CodeGenerationError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Could not generate a unique short code. Please try again."
    default_code = "code_generation_failed"


def create_short_url(*, owner, original_url: str, expires_at=None) -> ShortURL:
    for _ in range(MAX_CODE_ATTEMPTS):
        code = generate_code()
        if code.lower() in RESERVED_CODES:
            continue
        try:
            with transaction.atomic():
                return ShortURL.objects.create(
                    owner=owner, short_code=code,
                    original_url=original_url, expires_at=expires_at,
                )
        except IntegrityError:
            continue

    logger.error("Failed to generate a unique short code after %s attempts", MAX_CODE_ATTEMPTS)
    raise CodeGenerationError()


def update_short_url(*, short_url: ShortURL, **fields) -> ShortURL:
    changed = [name for name in fields if name in UPDATABLE_FIELDS]
    for name in changed:
        setattr(short_url, name, fields[name])
    if changed:
        short_url.save(update_fields=[*changed, "updated_at"])
        invalidate_cache(short_url.short_code)
    return short_url


def delete_short_url(*, short_url: ShortURL) -> None:
    code = short_url.short_code
    short_url.delete()
    invalidate_cache(code)


def invalidate_cache(short_code: str) -> None:
    try:
        cache.delete(cache_key(short_code))
    except Exception:
        logger.warning("Cache invalidation failed for %s", short_code, exc_info=True)
