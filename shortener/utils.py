import secrets
import string

from django.conf import settings

BASE62_ALPHABET = string.ascii_letters + string.digits


def generate_code(length: int | None = None) -> str:
    """Cryptographically random base62 code (not guessable or enumerable)."""
    length = length or getattr(settings, "SHORT_CODE_LENGTH", 7)
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))


def cache_key(short_code: str) -> str:
    return f"short:{short_code}"


def build_short_url(short_code: str) -> str:
    base = settings.BASE_SHORT_URL.rstrip("/")
    return f"{base}/{short_code}"
