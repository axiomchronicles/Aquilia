"""
Auth Module Serializers.

Defines input validation and output formatting for auth operations.
"""

from typing import Any
from aquilia.serializers import (
    Serializer,
    ModelSerializer,
    CharField,
    EmailField,
    IntegerField,
    BooleanField,
    ImageField,
)
from aquilia.serializers.exceptions import ValidationFault

from .models import User


class RegisterSerializer(Serializer):
    """Validate registration input."""
    email = EmailField(required=True)
    password = CharField(write_only=True, min_length=6, required=True)
    full_name = CharField(required=False, max_length=255)


class LoginSerializer(Serializer):
    """Validate login input."""
    email = EmailField(required=True)
    password = CharField(write_only=True, required=True)


class UserSerializer(Serializer):
    """Serialize user data for output."""
    id = IntegerField(read_only=True)
    email = EmailField(read_only=True)
    full_name = CharField(read_only=True)
    is_active = BooleanField(read_only=True)


# Keep old name as alias for backwards compatibility
RegisterSerilizer = RegisterSerializer