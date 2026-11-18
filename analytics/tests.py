from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from shortener.models import ShortURL

from . import selectors, services
from .models import Click
from .tasks import record_click_task
from .utils import (
    anonymize_ip,
    clean_country,
    extract_domain,
    get_client_ip,
    parse_user_agent,
)

User = get_user_model()

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
BOT_UA = "Googlebot/2.1 (+http://www.google.com/bot.html)"


def make_user(email="owner@example.com"):
    return User.objects.create_user(email=email, password="S3cure-pass!")


def make_url(owner, code="abc123"):
    return ShortURL.objects.create(owner=owner, short_code=code, original_url="https://example.com")


def make_click(short_url, when=None, **kwargs):
    defaults = {"device_type": "desktop", "browser": "Chrome"}
    defaults.update(kwargs)
    return Click.objects.create(short_url=short_url, clicked_at=when or timezone.now(), **defaults)


class UtilsTests(TestCase):
    def test_anonymize_ipv4_zeroes_last_octet(self):
        self.assertEqual(anonymize_ip("203.0.113.45"), "203.0.113.0")

    def test_anonymize_ipv6_truncates_to_48_bits(self):
        self.assertEqual(anonymize_ip("2001:db8:abcd:1234::1"), "2001:db8:abcd::")

    def test_anonymize_invalid_or_empty_returns_none(self):
        self.assertIsNone(anonymize_ip("not-an-ip"))
        self.assertIsNone(anonymize_ip(""))
        self.assertIsNone(anonymize_ip(None))

    @override_settings(ANALYTICS_ANONYMIZE_IP=False)
    def test_anonymize_can_be_disabled(self):
        self.assertEqual(anonymize_ip("203.0.113.45"), "203.0.113.45")

    def test_extract_domain(self):
        self.assertEqual(extract_domain("https://Www.Google.com/search?q=1"), "www.google.com")
        self.assertEqual(extract_domain(""), "")

    def test_clean_country(self):
        self.assertEqual(clean_country("in"), "IN")
        for bad in ("XX", "T1", "India", "", None):
            self.assertEqual(clean_country(bad), "")

    def test_parse_user_agent(self):
        desktop = parse_user_agent(CHROME_UA)
        self.assertEqual((desktop.device_type, desktop.browser), ("desktop", "Chrome"))
        self.assertEqual(parse_user_agent(IPHONE_UA).device_type, "mobile")
        self.assertEqual(parse_user_agent(BOT_UA).device_type, "bot")
        empty = parse_user_agent("")
        self.assertEqual((empty.device_type, empty.browser), ("other", ""))

    def test_client_ip_ignores_forwarded_header_by_default(self):
        request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    @override_settings(ANALYTICS_TRUST_PROXY=True)
    def test_client_ip_uses_first_forwarded_address_when_trusted(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "1.2.3.4")


class ClickModelTests(TestCase):
    def setUp(self):
        self.short_url = make_url(make_user())

    def test_default_ordering_is_newest_first(self):
        now = timezone.now()
        old = make_click(self.short_url, now - timedelta(days=1))
        new = make_click(self.short_url, now)
        self.assertEqual(list(Click.objects.all()), [new, old])

    def test_clicks_are_deleted_with_their_short_url(self):
        make_click(self.short_url)
        self.short_url.delete()
        self.assertEqual(Click.objects.count(), 0)


class ServiceTests(TestCase):
    def setUp(self):
        self.short_url = make_url(make_user())

    def test_record_click_stores_parsed_and_anonymized_data(self):
        click = services.record_click(
            short_code="abc123",
            clicked_at=timezone.now(),
            ip_address="203.0.113.45",
            user_agent=CHROME_UA,
            referrer="https://www.google.com/search",
            country="in",
        )
        self.assertEqual(click.short_url, self.short_url)
        self.assertEqual(click.ip_address, "203.0.113.0")
        self.assertEqual(click.referrer_domain, "www.google.com")
        self.assertEqual(click.country, "IN")
        self.assertEqual(click.device_type, "desktop")
        self.assertEqual(click.browser, "Chrome")

    def test_record_click_for_unknown_code_returns_none(self):
        result = services.record_click(
            short_code="missing", clicked_at=timezone.now(), ip_address="",
            user_agent="", referrer="", country="",
        )
        self.assertIsNone(result)
        self.assertEqual(Click.objects.count(), 0)

    def test_track_click_queues_task_with_request_metadata(self):
        request = RequestFactory().get(
            "/abc123", REMOTE_ADDR="203.0.113.45", HTTP_USER_AGENT=CHROME_UA,
            HTTP_REFERER="https://google.com/", HTTP_CF_IPCOUNTRY="IN",
        )
        with patch("analytics.tasks.record_click_task.apply_async") as queued:
            services.track_click(request, "abc123")

        queued.assert_called_once()
        code, metadata = queued.call_args.kwargs["args"]
        self.assertEqual(code, "abc123")
        self.assertEqual(metadata["ip_address"], "203.0.113.45")
        self.assertEqual(metadata["user_agent"], CHROME_UA)
        self.assertEqual(metadata["referrer"], "https://google.com/")
        self.assertEqual(metadata["country"], "IN")
        self.assertFalse(queued.call_args.kwargs["retry"])

    def test_track_click_never_raises_when_broker_is_down(self):
        request = RequestFactory().get("/abc123")
        with patch("analytics.tasks.record_click_task.apply_async", side_effect=Exception("down")):
            services.track_click(request, "abc123")  # must not raise

    def test_task_writes_click(self):
        record_click_task(
            "abc123",
            {
                "clicked_at": timezone.now().isoformat(),
                "ip_address": "198.51.100.7",
                "user_agent": IPHONE_UA,
                "referrer": "",
                "country": "",
            },
        )
        click = Click.objects.get()
        self.assertEqual(click.device_type, "mobile")
        self.assertEqual(click.ip_address, "198.51.100.0")


class SelectorTests(TestCase):
    def setUp(self):
        self.short_url = make_url(make_user())
        self.base = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.get_current_timezone())

    def test_summary_counts_and_breakdowns(self):
        make_click(self.short_url, self.base, country="IN", referrer_domain="google.com")
        make_click(self.short_url, self.base, country="IN", referrer_domain="google.com")
        make_click(self.short_url, self.base, country="US", device_type="mobile", browser="Safari")
        make_click(self.short_url, self.base, country="", referrer_domain="")  # blanks excluded

        summary = selectors.get_summary(
            short_url=self.short_url,
            start=self.base - timedelta(days=1),
            end=self.base + timedelta(days=1),
        )

        self.assertEqual(summary["total_clicks"], 4)
        self.assertEqual(summary["countries"][0], {"country": "IN", "count": 2})
        self.assertEqual(len(summary["countries"]), 2)  # blank country excluded
        self.assertEqual(summary["referrers"], [{"referrer_domain": "google.com", "count": 2}])
        self.assertEqual(
            {d["device_type"]: d["count"] for d in summary["devices"]},
            {"desktop": 3, "mobile": 1},
        )

    def test_summary_respects_date_range_and_link(self):
        other = make_url(make_user("other@example.com"), code="zzz999")
        make_click(self.short_url, self.base)
        make_click(self.short_url, self.base - timedelta(days=30))  # outside range
        make_click(other, self.base)  # different link

        summary = selectors.get_summary(
            short_url=self.short_url,
            start=self.base - timedelta(days=1),
            end=self.base + timedelta(days=1),
        )
        self.assertEqual(summary["total_clicks"], 1)

    def test_timeseries_daily_fills_empty_buckets(self):
        make_click(self.short_url, self.base - timedelta(days=2))
        make_click(self.short_url, self.base)
        make_click(self.short_url, self.base)

        result = selectors.get_timeseries(
            short_url=self.short_url,
            start=self.base - timedelta(days=3),
            end=self.base + timedelta(hours=1),
            interval="day",
        )
        self.assertEqual([p["clicks"] for p in result["data"]], [0, 1, 0, 2])

    def test_timeseries_hourly(self):
        make_click(self.short_url, self.base)
        make_click(self.short_url, self.base + timedelta(minutes=30))
        make_click(self.short_url, self.base + timedelta(hours=2))

        result = selectors.get_timeseries(
            short_url=self.short_url,
            start=self.base - timedelta(hours=1),
            end=self.base + timedelta(hours=3),
            interval="hour",
        )
        self.assertEqual([p["clicks"] for p in result["data"]], [0, 2, 0, 1, 0])

    def test_timeseries_weekly_buckets_start_on_monday(self):
        tz = timezone.get_current_timezone()
        make_click(self.short_url, datetime(2026, 10, 10, 9, 0, tzinfo=tz))
        make_click(self.short_url, datetime(2026, 10, 14, 9, 0, tzinfo=tz))
        make_click(self.short_url, datetime(2026, 10, 14, 15, 0, tzinfo=tz))

        result = selectors.get_timeseries(
            short_url=self.short_url,
            start=datetime(2026, 10, 10, 0, 0, tzinfo=tz),
            end=datetime(2026, 10, 20, 0, 0, tzinfo=tz),
            interval="week",
        )
        self.assertEqual(result["data"][0]["timestamp"].weekday(), 0)
        self.assertEqual([p["clicks"] for p in result["data"]], [1, 2, 0])


class AnalyticsAPITests(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.other = make_user("other@example.com")
        self.short_url = make_url(self.owner)
        make_click(self.short_url, timezone.now() - timedelta(hours=1), country="IN")
        make_click(self.short_url, timezone.now() - timedelta(days=2), country="US")
        self.client = APIClient()
        self.summary_url = reverse("analytics-summary", kwargs={"pk": self.short_url.pk})
        self.series_url = reverse("analytics-timeseries", kwargs={"pk": self.short_url.pk})

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.summary_url).status_code, 401)
        self.assertEqual(self.client.get(self.series_url).status_code, 401)

    def test_owner_gets_summary_for_default_30_day_range(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.summary_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_clicks"], 2)
        self.assertEqual(response.data["short_code"], "abc123")

    def test_other_users_get_404(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.summary_url).status_code, 404)
        self.assertEqual(self.client.get(self.series_url).status_code, 404)

    def test_unknown_link_returns_404(self):
        self.client.force_authenticate(self.owner)
        url = reverse("analytics-summary", kwargs={"pk": 99999})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_timeseries_defaults_to_daily(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.series_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["interval"], "day")
        self.assertEqual(sum(p["clicks"] for p in response.data["data"]), 2)

    def test_invalid_interval_is_rejected(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(self.series_url, {"interval": "minute"}).status_code, 400)

    def test_start_must_be_before_end(self):
        self.client.force_authenticate(self.owner)
        now = timezone.now()
        response = self.client.get(
            self.summary_url, {"start": now.isoformat(), "end": (now - timedelta(days=1)).isoformat()}
        )
        self.assertEqual(response.status_code, 400)

    def test_range_is_capped_at_366_days(self):
        self.client.force_authenticate(self.owner)
        now = timezone.now()
        response = self.client.get(
            self.summary_url, {"start": (now - timedelta(days=400)).isoformat(), "end": now.isoformat()}
        )
        self.assertEqual(response.status_code, 400)

    def test_hourly_interval_limited_to_seven_days(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.series_url, {"interval": "hour"})  # default range is 30 days
        self.assertEqual(response.status_code, 400)

    def test_analytics_summary_datetime_am_pm_format(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, 200)
        am_pm_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (AM|PM)$"
        self.assertRegex(response.data["period"]["start"], am_pm_pattern)
        self.assertRegex(response.data["period"]["end"], am_pm_pattern)

    def test_analytics_timeseries_datetime_am_pm_format(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.series_url)
        self.assertEqual(response.status_code, 200)
        am_pm_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (AM|PM)$"
        self.assertRegex(response.data["period"]["start"], am_pm_pattern)
        self.assertRegex(response.data["period"]["end"], am_pm_pattern)
        for point in response.data["data"]:
            self.assertRegex(point["timestamp"], am_pm_pattern)


class RedirectIntegrationTests(TestCase):
    """Requires `track_click(request, short_code)` to be called in shortener/views.py."""

    def setUp(self):
        cache.clear()
        self.short_url = make_url(make_user())
        self.client = Client()

    def test_redirect_calls_track_click(self):
        with patch("shortener.views.track_click") as track:
            response = self.client.get("/abc123")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://example.com")
        track.assert_called_once()
        self.assertEqual(track.call_args.args[1], "abc123")

    def test_unknown_code_does_not_track(self):
        with patch("shortener.views.track_click") as track:
            response = self.client.get("/nope123")

        self.assertEqual(response.status_code, 404)
        track.assert_not_called()

    def test_redirect_records_click_end_to_end(self):
        def run_inline(args, retry=False):
            record_click_task(*args)

        with patch("analytics.tasks.record_click_task.apply_async", side_effect=run_inline):
            self.client.get(
                "/abc123", HTTP_USER_AGENT=CHROME_UA, HTTP_REFERER="https://news.ycombinator.com/"
            )

        click = Click.objects.get()
        self.assertEqual(click.short_url, self.short_url)
        self.assertEqual(click.referrer_domain, "news.ycombinator.com")
        self.assertEqual(click.device_type, "desktop")
