import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_with_email_and_password(self):
        user = User.objects.create_user(email="ann@example.com", password="S3cure-pass!")

        self.assertEqual(user.email, "ann@example.com")
        self.assertTrue(user.check_password("S3cure-pass!"))
        self.assertNotEqual(user.password, "S3cure-pass!")  # stored hashed
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_normalizes_email_to_lowercase(self):
        user = User.objects.create_user(email="Ann@EXAMPLE.com", password="S3cure-pass!")
        self.assertEqual(user.email, "ann@example.com")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="S3cure-pass!")

    def test_create_user_without_password_sets_unusable_password(self):
        user = User.objects.create_user(email="nopass@example.com")
        self.assertFalse(user.has_usable_password())

    def test_create_user_saves_extra_fields(self):
        user = User.objects.create_user(
            email="ann@example.com", password="S3cure-pass!", full_name="Ann Lee"
        )
        user.refresh_from_db()
        self.assertEqual(user.full_name, "Ann Lee")

    def test_duplicate_email_raises_integrity_error(self):
        User.objects.create_user(email="ann@example.com", password="S3cure-pass!")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(email="ann@example.com", password="Other-pass1!")

    def test_duplicate_email_with_different_case_raises(self):
        User.objects.create_user(email="ann@example.com", password="S3cure-pass!")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(email="ANN@Example.com", password="Other-pass1!")

    def test_create_superuser_sets_flags(self):
        admin = User.objects.create_superuser(email="root@example.com", password="S3cure-pass!")

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_create_superuser_requires_is_staff_true(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="root@example.com", password="S3cure-pass!", is_staff=False
            )

    def test_create_superuser_requires_is_superuser_true(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="root@example.com", password="S3cure-pass!", is_superuser=False
            )


class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ann@example.com", password="S3cure-pass!", full_name="Ann Lee"
        )

    def test_uses_custom_user_model(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")
        self.assertEqual(User._meta.label, "accounts.User")

    def test_primary_key_is_uuid(self):
        self.assertIsInstance(self.user.pk, uuid.UUID)

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, ["full_name"])

    def test_str_returns_email(self):
        self.assertEqual(str(self.user), "ann@example.com")

    def test_full_name_is_optional(self):
        user = User.objects.create_user(email="bob@example.com", password="S3cure-pass!")
        self.assertEqual(user.full_name, "")

    def test_date_joined_defaults_to_now(self):
        self.assertLess(timezone.now() - self.user.date_joined, timedelta(seconds=10))

    def test_default_ordering_is_newest_first(self):
        older = User.objects.create_user(
            email="old@example.com",
            password="S3cure-pass!",
            date_joined=timezone.now() - timedelta(days=5),
        )
        newer = User.objects.create_user(
            email="new@example.com",
            password="S3cure-pass!",
            date_joined=timezone.now() + timedelta(days=5),
        )

        emails = list(User.objects.values_list("email", flat=True))
        self.assertEqual(emails[0], newer.email)
        self.assertEqual(emails[-1], older.email)

    def test_set_password_changes_hash(self):
        old_hash = self.user.password
        self.user.set_password("An0ther-str0ng-pass")
        self.user.save()
        self.user.refresh_from_db()

        self.assertNotEqual(self.user.password, old_hash)
        self.assertTrue(self.user.check_password("An0ther-str0ng-pass"))
        self.assertFalse(self.user.check_password("S3cure-pass!"))

    def test_regular_user_has_no_permissions(self):
        self.assertFalse(self.user.has_perm("auth.add_user"))
        self.assertFalse(self.user.is_staff)

    def test_superuser_has_all_permissions(self):
        admin = User.objects.create_superuser(email="root@example.com", password="S3cure-pass!")
        self.assertTrue(admin.has_perm("auth.add_user"))
        self.assertTrue(admin.has_module_perms("accounts"))


class UserAuthenticationTests(TestCase):
    def setUp(self):
        self.password = "S3cure-pass!"
        self.user = User.objects.create_user(email="ann@example.com", password=self.password)

    def test_authenticate_with_email_and_password(self):
        authenticated = authenticate(username="ann@example.com", password=self.password)
        self.assertEqual(authenticated, self.user)

    def test_authenticate_fails_with_wrong_password(self):
        self.assertIsNone(authenticate(username="ann@example.com", password="wrong"))

    def test_authenticate_fails_for_unknown_email(self):
        self.assertIsNone(authenticate(username="ghost@example.com", password=self.password))

    def test_inactive_user_cannot_authenticate(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.assertIsNone(authenticate(username="ann@example.com", password=self.password))
