from celery import shared_task
from django.db import OperationalError
from django.utils.dateparse import parse_datetime

from . import services


@shared_task(
    ignore_result=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def record_click_task(short_code: str, metadata: dict) -> None:
    services.record_click(
        short_code=short_code,
        clicked_at=parse_datetime(metadata["clicked_at"]),
        ip_address=metadata.get("ip_address", ""),
        user_agent=metadata.get("user_agent", ""),
        referrer=metadata.get("referrer", ""),
        country=metadata.get("country", ""),
    )
