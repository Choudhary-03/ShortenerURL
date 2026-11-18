from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

User = get_user_model()


def create_user(*, email: str, password: str, full_name: str = "") -> User:
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": "A user with this email already exists."})
    return User.objects.create_user(email=email, password=password, full_name=full_name)


def change_password(*, user: User, old_password: str, new_password: str) -> None:
    if not user.check_password(old_password):
        raise ValidationError({"old_password": "Incorrect password."})
    user.set_password(new_password)
    user.save(update_fields=["password"])
