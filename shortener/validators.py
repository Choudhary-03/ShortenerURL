import ipaddress
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

ALLOWED_SCHEMES = {"http", "https"}
MAX_URL_LENGTH = 2048

ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
RESERVED_CODES = {
    "admin", "api", "static", "media", "health", "metrics",
    "docs", "login", "logout", "register", "favicon.ico", "robots.txt",
}


def validate_original_url(value: str) -> None:
    if len(value) > MAX_URL_LENGTH:
        raise ValidationError(f"URL must be at most {MAX_URL_LENGTH} characters.")

    parsed = urlparse(value)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValidationError("Only http and https URLs are allowed.")

    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationError("URL must include a valid host.")

    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValidationError("Local addresses are not allowed.")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and (ip.is_private or ip.is_loopback or ip.is_link_local
               or ip.is_reserved or ip.is_unspecified or ip.is_multicast):
        raise ValidationError("Private or reserved IP addresses are not allowed.")

    own_host = (urlparse(settings.BASE_SHORT_URL).hostname or "").lower()
    if own_host and host == own_host:
        raise ValidationError("Cannot shorten a link that points to this service.")


def validate_alias(value: str) -> None:
    if not ALIAS_PATTERN.match(value):
        raise ValidationError(
            "Alias must be 3-32 characters: letters, numbers, hyphens, or underscores."
        )
    if value.lower() in RESERVED_CODES:
        raise ValidationError("This alias is reserved.")


def validate_future_datetime(value) -> None:
    if value is not None and value <= timezone.now():
        raise ValidationError("Expiry must be in the future.")
