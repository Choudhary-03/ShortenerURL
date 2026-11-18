from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDay, TruncHour, TruncWeek
from django.shortcuts import get_object_or_404
from django.utils import timezone

from shortener.selectors import get_user_urls

from .models import Click

TRUNC = {"hour": TruncHour, "day": TruncDay, "week": TruncWeek}
STEP = {"hour": timedelta(hours=1), "day": timedelta(days=1), "week": timedelta(weeks=1)}
TOP_N = 10


def get_owned_short_url(*, owner, pk):
    return get_object_or_404(get_user_urls(owner=owner), pk=pk)


def _clicks(short_url, start, end):
    return Click.objects.filter(short_url=short_url, clicked_at__gte=start, clicked_at__lte=end)


def _breakdown(qs, field: str, limit: int = TOP_N) -> list[dict]:
    return list(
        qs.exclude(**{field: ""})
        .values(field)
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )


def get_summary(*, short_url, start, end) -> dict:
    tz = timezone.get_current_timezone()
    start_tz = start.astimezone(tz)
    end_tz = end.astimezone(tz)
    qs = _clicks(short_url, start_tz, end_tz)
    return {
        "short_url_id": short_url.id,
        "short_code": short_url.short_code,
        "period": {"start": start_tz, "end": end_tz},
        "total_clicks": qs.count(),
        "devices": _breakdown(qs, "device_type"),
        "browsers": _breakdown(qs, "browser"),
        "countries": _breakdown(qs, "country"),
        "referrers": _breakdown(qs, "referrer_domain"),
    }


def _floor(value, interval: str):
    tz = timezone.get_current_timezone()
    value = value.astimezone(tz)
    if interval == "hour":
        return value.replace(minute=0, second=0, microsecond=0)
    day = value.replace(hour=0, minute=0, second=0, microsecond=0)
    if interval == "day":
        return day
    return day - timedelta(days=day.weekday())  # week starts Monday


def get_timeseries(*, short_url, start, end, interval: str) -> dict:
    tz = timezone.get_current_timezone()
    start_tz = start.astimezone(tz)
    end_tz = end.astimezone(tz)

    rows = (
        _clicks(short_url, start_tz, end_tz)
        .annotate(bucket=TRUNC[interval]("clicked_at", tzinfo=tz))
        .values("bucket")
        .annotate(clicks=Count("id"))
        .order_by("bucket")
    )
    counts = {row["bucket"]: row["clicks"] for row in rows}

    # Fill empty buckets with zero so charts have a continuous axis.
    points, cursor = [], _floor(start_tz, interval)
    while cursor <= end_tz:
        points.append({"timestamp": cursor, "clicks": counts.get(cursor, 0)})
        cursor += STEP[interval]

    return {
        "short_url_id": short_url.id,
        "short_code": short_url.short_code,
        "interval": interval,
        "period": {"start": start_tz, "end": end_tz},
        "data": points,
    }
