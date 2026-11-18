from zoneinfo import ZoneInfo

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

IST = ZoneInfo("Asia/Kolkata")

DATETIME_INPUT_FORMATS = [
    "%Y-%m-%d %I:%M:%S %p",
    "%Y-%m-%d %I:%M %p",
    "%d-%m-%Y %I:%M:%S %p",
    "%d-%m-%Y %I:%M %p",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %I:%M:%S %p",
    "%d/%m/%Y %I:%M %p",
    "iso-8601",
]


@extend_schema_field({
    "type": "string",
    "example": "2026-11-18 02:30:00 PM",
    "description": "IST datetime in AM/PM format (YYYY-MM-DD hh:mm:ss AM/PM)",
})
class ISTDateTimeField(serializers.DateTimeField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d %I:%M:%S %p")
        kwargs.setdefault("input_formats", DATETIME_INPUT_FORMATS)
        kwargs.setdefault("default_timezone", IST)
        super().__init__(*args, **kwargs)

    def enforce_timezone(self, value):
        if value is None:
            return None
        if timezone.is_aware(value):
            return value.astimezone(IST)
        return timezone.make_aware(value, IST)
