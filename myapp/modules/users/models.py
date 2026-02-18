"""
Users Module — Models

Aquilia pure-Python ORM models for user management.
Uses metaclass-driven field definitions with Django-grade capabilities.
"""

from aquilia.models import (
    Model,
    CharField,
    EmailField,
    TextField,
    BooleanField,
    DateTimeField,
    IntegerField,
    JSONField,
    UUIDField,
    ForeignKey,
    Index,
    UniqueConstraint,
    CASCADE,
)
from aquilia.models.enums import TextChoices


class UserRole(TextChoices):
    """User roles for RBAC."""
    CUSTOMER = "customer", "Customer"
    VENDOR = "vendor", "Vendor"
    MODERATOR = "moderator", "Moderator"
    ADMIN = "admin", "Administrator"
    SUPERADMIN = "superadmin", "Super Administrator"


class User(Model):
    """
    Core user model.

    Stores identity, credentials, and profile data.
    Integrated with Aquilia Auth for session/token binding.
    """
    table = "users"

    uuid = UUIDField(unique=True, editable=False)
    email = EmailField(max_length=255, unique=True)
    username = CharField(max_length=150, unique=True)
    password_hash = CharField(max_length=255)
    first_name = CharField(max_length=100, default="")
    last_name = CharField(max_length=100, default="")
    role = CharField(max_length=20, default=UserRole.CUSTOMER)
    is_active = BooleanField(default=True)
    is_verified = BooleanField(default=False)
    avatar_url = CharField(max_length=500, null=True)
    bio = TextField(null=True)
    phone = CharField(max_length=20, null=True)
    preferences = JSONField(default=dict)
    last_login_at = DateTimeField(null=True)
    login_count = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["email"]),
            Index(fields=["username"]),
            Index(fields=["role", "is_active"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.email})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.SUPERADMIN)


class UserAddress(Model):
    """User shipping/billing addresses."""
    table = "user_addresses"

    user = ForeignKey("User", on_delete=CASCADE, related_name="addresses")
    label = CharField(max_length=50, default="home")
    street_address = CharField(max_length=255)
    city = CharField(max_length=100)
    state = CharField(max_length=100)
    postal_code = CharField(max_length=20)
    country = CharField(max_length=2, default="US")
    is_default = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]


class UserSession(Model):
    """
    Persistent session tracking for analytics and security.
    Complements Aquilia's in-memory SessionEngine.
    """
    table = "user_sessions"

    user = ForeignKey("User", on_delete=CASCADE, related_name="sessions")
    session_id = CharField(max_length=255, unique=True)
    ip_address = CharField(max_length=45)
    user_agent = CharField(max_length=500, null=True)
    device_fingerprint = CharField(max_length=255, null=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    last_activity = DateTimeField(auto_now=True)
    expires_at = DateTimeField(null=True)

    class Meta:
        ordering = ["-last_activity"]
        indexes = [
            Index(fields=["session_id"]),
            Index(fields=["user", "is_active"]),
        ]
