from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors
from .serializers import (
    AnalyticsQuerySerializer,
    ClickSummarySerializer,
    ClickTimeseriesSerializer,
)


def _params(request) -> dict:
    serializer = AnalyticsQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class ClickSummaryView(APIView):
    """Totals and breakdowns. Non-owners get 404 (link IDs are not revealed)."""

    @extend_schema(
        tags=["Analytics"], summary="Click totals and breakdowns",
        parameters=[AnalyticsQuerySerializer], responses=ClickSummarySerializer,
    )
    def get(self, request, pk):
        short_url = selectors.get_owned_short_url(owner=request.user, pk=pk)
        params = _params(request)
        data = selectors.get_summary(short_url=short_url, start=params["start"], end=params["end"])
        return Response(ClickSummarySerializer(data).data)


class ClickTimeseriesView(APIView):
    @extend_schema(
        tags=["Analytics"], summary="Clicks over time",
        parameters=[AnalyticsQuerySerializer], responses=ClickTimeseriesSerializer,
    )
    def get(self, request, pk):
        short_url = selectors.get_owned_short_url(owner=request.user, pk=pk)
        params = _params(request)
        data = selectors.get_timeseries(
            short_url=short_url,
            start=params["start"],
            end=params["end"],
            interval=params["interval"],
        )
        return Response(ClickTimeseriesSerializer(data).data)
