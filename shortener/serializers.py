from rest_framework import serializers

from config.fields import ISTDateTimeField

from .models import ShortURL
from .utils import build_short_url
from .validators import validate_future_datetime, validate_original_url


class ShortURLSerializer(serializers.ModelSerializer):
    short_url = serializers.SerializerMethodField()
    expires_at = ISTDateTimeField(required=False, allow_null=True)
    created_at = ISTDateTimeField(read_only=True)
    updated_at = ISTDateTimeField(read_only=True)

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
    expires_at = ISTDateTimeField(
        required=False, allow_null=True, validators=[validate_future_datetime]
    )


class UpdateShortURLSerializer(serializers.Serializer):
    original_url = serializers.URLField(
        max_length=2048, required=False, validators=[validate_original_url]
    )
    is_active = serializers.BooleanField(required=False)
    expires_at = ISTDateTimeField(
        required=False, allow_null=True, validators=[validate_future_datetime]
    )
