from django.urls import path

from .views import ClickSummaryView, ClickTimeseriesView

# Mounted at /api/v1/urls/ (alongside shortener.urls)
urlpatterns = [
    path("<int:pk>/analytics/", ClickSummaryView.as_view(), name="analytics-summary"),
    path("<int:pk>/analytics/timeseries/", ClickTimeseriesView.as_view(), name="analytics-timeseries"),
]
