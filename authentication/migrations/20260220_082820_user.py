"""
Migration: 20260220_082820_user
Generated: 2026-02-20T08:28:20.280294+00:00
Models: User
"""

from aquilia.models.migration_dsl import (
    AddField,
    columns as C,
)


class Meta:
    revision = "20260220_082820"
    slug = "user"
    models = ['User']


operations = [
    AddField(
        model_name='User', table='auth_users',
        column=C.varchar("profile", 255),
    ),
]
