"""
Migration: 20260219_090659_users
Generated: 2026-02-19T09:06:59.060288+00:00
Models: Users
"""

from aquilia.models.migration_dsl import (
    CreateIndex, CreateModel,
    columns as C,
)


class Meta:
    revision = "20260219_090659"
    slug = "users"
    models = ['Users']


operations = [
    CreateModel(
        name='Users',
        table='users',
        fields=[
            C.auto("id"),
            C.varchar("name", 150),
            C.varchar("email", 254, unique=True),
            C.varchar("password", 255),
            C.integer("active", default=False),
            C.timestamp("created_at"),
        ],
    ),
    CreateIndex(
        name='idx_users_email', table='users',
        columns=['email'], unique=False,
    ),
]
