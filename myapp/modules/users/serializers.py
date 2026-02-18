"""
Users Module — Serializers

Aquilia Serializer/ModelSerializer with DI-aware defaults,
nested relations, custom validation, and write-only fields.
"""

from aquilia.serializers import (
    Serializer,
    ModelSerializer,
    ListSerializer,
    CharField,
    EmailField,
    IntegerField,
    BooleanField,
    DateTimeField,
    JSONField,
    UUIDField,
    SlugRelatedField,
    PrimaryKeyRelatedField,
    CurrentUserDefault,
)

from .models import User, UserAddress, UserSession


# ─── Authentication Serializers ──────────────────────────────────

class LoginSerializer(Serializer):
    """Validates login credentials."""
    email = EmailField(required=True)
    password = CharField(required=True, write_only=True, min_length=8)


class RegisterSerializer(Serializer):
    """Validates new user registration data."""
    email = EmailField(required=True)
    username = CharField(required=True, min_length=3, max_length=150)
    password = CharField(required=True, write_only=True, min_length=8, max_length=128)
    password_confirm = CharField(required=True, write_only=True)
    first_name = CharField(required=False, max_length=100, default="")
    last_name = CharField(required=False, max_length=100, default="")

    def validate_username(self, value: str) -> str:
        if not value.isalnum() and "_" not in value:
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return value.lower()

    def validate(self, data: dict) -> dict:
        if data.get("password") != data.get("password_confirm"):
            raise ValueError("Passwords do not match")
        data.pop("password_confirm", None)
        return data


class PasswordChangeSerializer(Serializer):
    """Validates password change request."""
    current_password = CharField(required=True, write_only=True)
    new_password = CharField(required=True, write_only=True, min_length=8, max_length=128)
    new_password_confirm = CharField(required=True, write_only=True)

    def validate(self, data: dict) -> dict:
        if data["new_password"] != data["new_password_confirm"]:
            raise ValueError("New passwords do not match")
        if data["current_password"] == data["new_password"]:
            raise ValueError("New password must differ from current password")
        data.pop("new_password_confirm", None)
        return data


# ─── User Serializers ─────────────────────────────────────────

class UserAddressSerializer(ModelSerializer):
    """Serializer for user addresses."""
    class Meta:
        model = UserAddress
        fields = [
            "id", "label", "street_address", "city",
            "state", "postal_code", "country", "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserPublicSerializer(ModelSerializer):
    """
    Public-facing user profile — safe for API exposure.
    Excludes sensitive fields (password, login_count, etc.).
    """
    full_name = CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "uuid", "username", "first_name", "last_name",
            "full_name", "avatar_url", "bio", "role",
            "created_at",
        ]
        read_only_fields = ["id", "uuid", "role", "created_at"]


class UserDetailSerializer(ModelSerializer):
    """
    Full user detail — for the authenticated user viewing their own profile.
    Includes addresses via nested serializer.
    """
    full_name = CharField(read_only=True)
    addresses = ListSerializer(child=UserAddressSerializer())

    class Meta:
        model = User
        fields = [
            "id", "uuid", "email", "username",
            "first_name", "last_name", "full_name",
            "role", "is_active", "is_verified",
            "avatar_url", "bio", "phone", "preferences",
            "last_login_at", "login_count",
            "addresses",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid", "email", "role", "is_active", "is_verified",
            "last_login_at", "login_count", "created_at", "updated_at",
        ]


class UserUpdateSerializer(ModelSerializer):
    """Validates profile update fields."""
    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "avatar_url",
            "bio", "phone", "preferences",
        ]


class UserAdminSerializer(ModelSerializer):
    """
    Admin-only serializer with all fields including management controls.
    """
    full_name = CharField(read_only=True)
    addresses = ListSerializer(child=UserAddressSerializer())

    class Meta:
        model = User
        fields = [
            "id", "uuid", "email", "username",
            "first_name", "last_name", "full_name",
            "role", "is_active", "is_verified",
            "avatar_url", "bio", "phone", "preferences",
            "last_login_at", "login_count",
            "addresses",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "uuid", "created_at", "updated_at"]


class UserListSerializer(ListSerializer):
    """Paginated list of users."""
    child = UserPublicSerializer()


# ─── Session Serializers ──────────────────────────────────────

class UserSessionSerializer(ModelSerializer):
    """Serializer for active user sessions (security panel)."""
    class Meta:
        model = UserSession
        fields = [
            "id", "session_id", "ip_address", "user_agent",
            "device_fingerprint", "is_active",
            "created_at", "last_activity", "expires_at",
        ]
        read_only_fields = [
            "id", "session_id", "ip_address", "user_agent",
            "device_fingerprint", "created_at", "last_activity",
        ]


# ─── Token Response ──────────────────────────────────────────

class AuthTokenSerializer(Serializer):
    """Response serializer for authentication tokens."""
    access_token = CharField(read_only=True)
    refresh_token = CharField(read_only=True)
    token_type = CharField(read_only=True, default="Bearer")
    expires_in = IntegerField(read_only=True)
    user = UserPublicSerializer(read_only=True)
