"""
Auth module models.
"""

from aquilia.models import Model
from aquilia.models.fields import (
    AutoField,
    CharField,
    BooleanField,
    DateTimeField,
    EmailField,
)


class User(Model):
    """
    User model for authentication.
    """
    table = "auth_users"

    id = AutoField(primary_key=True)
    profile = CharField(null=True)
    email = EmailField(unique=True, max_length=255)
    password_hash = CharField(max_length=255)
    full_name = CharField(max_length=255, null=True)
    is_active = BooleanField(default=True)
    is_superuser = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = []

    def __str__(self):
        return self.email
