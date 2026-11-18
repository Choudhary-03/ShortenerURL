import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings
from user_agents import parse as parse_ua

UNKNOWN_COUNTRIES = {"XX", "T1"}  # Cloudflare placeholders


@dataclass(frozen=True)
class ParsedUserAgent:
    device_type: str
    browser: str


def parse_user_agent(user_agent: str) -> ParsedUserAgent:
    if not user_agent:
        return ParsedUserAgent("other", "")
    ua = parse_ua(user_agent)
    if ua.is_bot:
        device = "bot"
    elif ua.is_mobile:
        device = "mobile"
    elif ua.is_tablet:
        device = "tablet"
    elif ua.is_pc:
        device = "desktop"
    else:
        device = "other"
    return ParsedUserAgent(device, (ua.browser.family or "")[:50])


def anonymize_ip(value: str | None) -> str | None:
    """Truncate to /24 (IPv4) or /48 (IPv6) unless ANALYTICS_ANONYMIZE_IP is False."""
    if not value:
        return None
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return None
    if not getattr(settings, "ANALYTICS_ANONYMIZE_IP", True):
        return str(ip)
    prefix = 24 if ip.version == 4 else 48
    network = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
    return str(network.network_address)


def get_client_ip(request) -> str | None:
    """Only trust X-Forwarded-For when running behind a proxy you control."""
    if getattr(settings, "ANALYTICS_TRUST_PROXY", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def extract_domain(referrer: str) -> str:
    if not referrer:
        return ""
    return (urlparse(referrer).hostname or "")[:255].lower()


def clean_country(value: str) -> str:
    value = (value or "").strip().upper()
    if len(value) == 2 and value.isalpha() and value not in UNKNOWN_COUNTRIES:
        return value
    return ""
