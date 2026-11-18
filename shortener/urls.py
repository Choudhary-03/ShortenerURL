from django.urls import path, re_path

from .views import ShortURLDetailView, ShortURLListCreateView, redirect_view

# Mounted at /api/v1/urls/
urlpatterns = [
    path("", ShortURLListCreateView.as_view(), name="shorturl-list"),
    path("<int:pk>/", ShortURLDetailView.as_view(), name="shorturl-detail"),
]

# Mounted at the site root. Must be the LAST pattern in config/urls.py.
redirect_patterns = [
    re_path(r"^(?P<short_code>[A-Za-z0-9_-]{3,32})/?$", redirect_view, name="redirect"),
]
