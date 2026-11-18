from datetime import timedelta
from datetime import timezone as dt_timezone

from django.db.models import Count
from django.db.models.functions import TruncDay, TruncHour, TruncWeek
from django.shortcuts import get_object_or_404

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
    qs = _clicks(short_url, start, end)
    return {
        "short_url_id": short_url.id,
        "short_code": short_url.short_code,
        "period": {"start": start, "end": end},
        "total_clicks": qs.count(),
        "devices": _breakdown(qs, "device_type"),
        "browsers": _breakdown(qs, "browser"),
        "countries": _breakdown(qs, "country"),
        "referrers": _breakdown(qs, "referrer_domain"),
    }


def _floor(value, interval: str):
    value = value.astimezone(dt_timezone.utc)
    if interval == "hour":
        return value.replace(minute=0, second=0, microsecond=0)
    day = value.replace(hour=0, minute=0, second=0, microsecond=0)
    if interval == "day":
        return day
    return day - timedelta(days=day.weekday())  # week starts Monday


def get_timeseries(*, short_url, start, end, interval: str) -> dict:
    start_utc = start.astimezone(dt_timezone.utc)
    end_utc = end.astimezone(dt_timezone.utc)

    rows = (
        _clicks(short_url, start_utc, end_utc)
        .annotate(bucket=TRUNC[interval]("clicked_at", tzinfo=dt_timezone.utc))
        .values("bucket")
        .annotate(clicks=Count("id"))
        .order_by("bucket")
    )
    counts = {row["bucket"]: row["clicks"] for row in rows}

    # Fill empty buckets with zero so charts have a continuous axis.
    points, cursor = [], _floor(start_utc, interval)
    while cursor <= end_utc:
        points.append({"timestamp": cursor, "clicks": counts.get(cursor, 0)})
        cursor += STEP[interval]

    return {
        "short_url_id": short_url.id,
        "short_code": short_url.short_code,
        "interval": interval,
        "period": {"start": start_utc, "end": end_utc},
        "data": points,
    }
