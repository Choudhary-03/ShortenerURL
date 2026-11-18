from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

DEFAULT_RANGE = timedelta(days=30)
MAX_RANGE = timedelta(days=366)
MAX_HOURLY_RANGE = timedelta(days=7)


class AnalyticsQuerySerializer(serializers.Serializer):
    """Query params: start, end (ISO 8601), interval (hour | day | week)."""

    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
    interval = serializers.ChoiceField(choices=["hour", "day", "week"], default="day")

    def validate(self, attrs):
        end = attrs.get("end") or timezone.now()
        start = attrs.get("start") or end - DEFAULT_RANGE
        interval = attrs["interval"]

        if start >= end:
            raise serializers.ValidationError({"start": "Must be before end."})
        if end - start > MAX_RANGE:
            raise serializers.ValidationError("Date range cannot exceed 366 days.")
        if interval == "hour" and end - start > MAX_HOURLY_RANGE:
            raise serializers.ValidationError(
                {"interval": "Hourly data is limited to a 7-day range."}
            )
        return {"start": start, "end": end, "interval": interval}


# ---- Response serializers (used for API documentation) ----
class CountSerializer(serializers.Serializer):
    count = serializers.IntegerField()


class DeviceCountSerializer(CountSerializer):
    device_type = serializers.CharField()


class BrowserCountSerializer(CountSerializer):
    browser = serializers.CharField()


class CountryCountSerializer(CountSerializer):
    country = serializers.CharField()


class ReferrerCountSerializer(CountSerializer):
    referrer_domain = serializers.CharField()


class PeriodSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class ClickSummarySerializer(serializers.Serializer):
    short_url_id = serializers.IntegerField()
    short_code = serializers.CharField()
    period = PeriodSerializer()
    total_clicks = serializers.IntegerField()
    devices = DeviceCountSerializer(many=True)
    browsers = BrowserCountSerializer(many=True)
    countries = CountryCountSerializer(many=True)
    referrers = ReferrerCountSerializer(many=True)


class TimeseriesPointSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    clicks = serializers.IntegerField()


class ClickTimeseriesSerializer(serializers.Serializer):
    short_url_id = serializers.IntegerField()
    short_code = serializers.CharField()
    interval = serializers.CharField()
    period = PeriodSerializer()
    data = TimeseriesPointSerializer(many=True)
