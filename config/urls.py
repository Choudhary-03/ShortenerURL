from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from shortener.urls import redirect_patterns

urlpatterns = [
    path("admin/", admin.site.urls),

    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API v1
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/urls/", include("shortener.urls")),
    path("api/v1/urls/", include("analytics.urls")),
]

# Public redirect catch-all: must stay LAST (and after /health/, /metrics/ when added)
urlpatterns += redirect_patterns
