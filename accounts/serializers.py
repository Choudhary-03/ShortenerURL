from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Output/profile serializer. Never exposes the password hash."""

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "date_joined")
        read_only_fields = ("id", "email", "date_joined")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value
