from django.http import Http404, HttpResponseRedirect
from django.views.decorators.http import require_safe
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsOwner
from analytics.services import track_click

from . import selectors, services
from .models import ShortURL
from .serializers import CreateShortURLSerializer, ShortURLSerializer, UpdateShortURLSerializer


@extend_schema_view(
    get=extend_schema(tags=["Short URLs"], summary="List your short URLs"),
    post=extend_schema(
        tags=["Short URLs"], summary="Create a short URL",
        request=CreateShortURLSerializer, responses={201: ShortURLSerializer},
    ),
)
class ShortURLListCreateView(generics.ListCreateAPIView):
    serializer_class = ShortURLSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ShortURL.objects.none()
        return selectors.get_user_urls(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = CreateShortURLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        short_url = services.create_short_url(owner=request.user, **serializer.validated_data)
        return Response(ShortURLSerializer(short_url).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=["Short URLs"], summary="Retrieve a short URL"),
    put=extend_schema(
        tags=["Short URLs"], summary="Update a short URL",
        request=UpdateShortURLSerializer, responses=ShortURLSerializer,
    ),
    patch=extend_schema(
        tags=["Short URLs"], summary="Partially update a short URL",
        request=UpdateShortURLSerializer, responses=ShortURLSerializer,
    ),
    delete=extend_schema(tags=["Short URLs"], summary="Delete a short URL"),
)
class ShortURLDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ShortURLSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ShortURL.objects.none()
        return selectors.get_user_urls(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = UpdateShortURLSerializer(
            instance, data=request.data, partial=kwargs.pop("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        instance = services.update_short_url(short_url=instance, **serializer.validated_data)
        return Response(ShortURLSerializer(instance).data)

    def perform_destroy(self, instance):
        services.delete_short_url(short_url=instance)


@require_safe
def redirect_view(request, short_code):
    """Public redirect: the hot path. Uses 302 so edits and deactivation take effect."""
    url = selectors.resolve_short_code(short_code)
    if url is None:
        raise Http404("Short URL not found or expired.")
    track_click(request, short_code)  # queued; never raises or blocks
    return HttpResponseRedirect(url)
