import logging
from datetime import datetime

from django.utils import timezone

from shortener.models import ShortURL

from .models import Click
from .utils import (
    anonymize_ip,
    clean_country,
    extract_domain,
    get_client_ip,
    parse_user_agent,
)

logger = logging.getLogger(__name__)


def track_click(request, short_code: str) -> None:
    """
    Called from the redirect view. Builds a small JSON-safe payload and queues a
    Celery task. Must never raise or slow down the redirect.
    """
    try:
        from .tasks import record_click_task  # local import avoids a circular import

        metadata = {
            "clicked_at": timezone.now().isoformat(),
            "ip_address": get_client_ip(request) or "",
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:512],
            "referrer": request.META.get("HTTP_REFERER", "")[:2048],
            "country": request.META.get("HTTP_CF_IPCOUNTRY", ""),
        }
        record_click_task.apply_async(args=[short_code, metadata], retry=False)
    except Exception:
        logger.warning("Could not queue click for %s", short_code, exc_info=True)


def record_click(*, short_code: str, clicked_at: datetime, ip_address: str,
                 user_agent: str, referrer: str, country: str) -> Click | None:
    """Runs in the Celery worker: resolve the link and store the click."""
    short_url_id = (
        ShortURL.objects.filter(short_code=short_code).values_list("id", flat=True).first()
    )
    if short_url_id is None:
        return None  # link was deleted between redirect and processing

    parsed = parse_user_agent(user_agent)
    return Click.objects.create(
        short_url_id=short_url_id,
        clicked_at=clicked_at,
        ip_address=anonymize_ip(ip_address),
        user_agent=user_agent,
        referrer=referrer,
        referrer_domain=extract_domain(referrer),
        country=clean_country(country),
        device_type=parsed.device_type,
        browser=parsed.browser,
    )
