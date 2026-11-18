import re
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import ShortURL
from .serializers import ShortURLSerializer

User = get_user_model()
AM_PM_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (AM|PM)$")


class TimezoneAndFormatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="S3cure-pass!")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_settings_timezone_is_ist(self):
        self.assertEqual(settings.TIME_ZONE, "Asia/Kolkata")

    def test_short_url_serializer_formats_datetime_in_ist_am_pm(self):
        expires_at = timezone.now() + timedelta(days=2)
        short_url = ShortURL.objects.create(
            owner=self.user,
            short_code="test123",
            original_url="https://example.com",
            expires_at=expires_at,
        )
        serializer = ShortURLSerializer(short_url)
        data = serializer.data

        self.assertRegex(data["created_at"], AM_PM_REGEX)
        self.assertRegex(data["updated_at"], AM_PM_REGEX)
        self.assertRegex(data["expires_at"], AM_PM_REGEX)

    def test_create_short_url_with_am_pm_expires_at(self):
        url = reverse("shorturl-list")
        future_ist_str = (timezone.localtime(timezone.now()) + timedelta(days=2)).strftime("%Y-%m-%d %I:%M:%S %p")
        response = self.client.post(
            url,
            {"original_url": "https://example.com/target", "expires_at": future_ist_str},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertRegex(response.data["created_at"], AM_PM_REGEX)
        self.assertRegex(response.data["expires_at"], AM_PM_REGEX)

    def test_user_serializer_date_joined_format(self):
        url = reverse("me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.data["date_joined"], AM_PM_REGEX)
