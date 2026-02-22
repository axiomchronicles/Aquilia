"""
Migration: 20260219_155011_user
Generated: 2026-02-19T15:50:11.698378+00:00
Models: User
"""

from aquilia.models.migration_dsl import (
    CreateModel,
    columns as C,
)


class Meta:
    revision = "20260219_155011"
    slug = "user"
    models = ['User']


operations = [
    CreateModel(
        name='User',
        table='auth_users',
        fields=[
            C.auto("id"),
            C.varchar("email", 255, unique=True),
            C.varchar("password_hash", 255),
            C.varchar("full_name", 255, null=True),
            C.integer("is_active", default=True),
            C.integer("is_superuser", default=False),
            C.timestamp("created_at"),
            C.timestamp("updated_at"),
        ],
    ),
]
