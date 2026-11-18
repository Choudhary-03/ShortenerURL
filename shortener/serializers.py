from rest_framework import serializers

from .models import ShortURL
from .utils import build_short_url
from .validators import validate_alias, validate_future_datetime, validate_original_url


class ShortURLSerializer(serializers.ModelSerializer):
    short_url = serializers.SerializerMethodField()

    class Meta:
        model = ShortURL
        fields = (
            "id", "short_code", "short_url", "original_url",
            "is_active", "expires_at", "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_short_url(self, obj) -> str:
        return build_short_url(obj.short_code)


class CreateShortURLSerializer(serializers.Serializer):
    original_url = serializers.URLField(max_length=2048, validators=[validate_original_url])
    custom_alias = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, validators=[validate_alias]
    )
    expires_at = serializers.DateTimeField(
        required=False, allow_null=True, validators=[validate_future_datetime]
    )

    def validate_custom_alias(self, value):
        return value or None


class UpdateShortURLSerializer(serializers.Serializer):
    original_url = serializers.URLField(
        max_length=2048, required=False, validators=[validate_original_url]
    )
    is_active = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(
        required=False, allow_null=True, validators=[validate_future_datetime]
    )
