from aquilia.models import Model
from aquilia.models.fields import (
    AutoField, CharField, EmailField, BooleanField,
    ForeignKey, Index, DateTimeField
)


class Users(Model):
    table = "users"

    id = AutoField()
    name = CharField(max_length = 150)
    email = EmailField(unique = True)
    password = CharField()
    active = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [Index(fields=["email"])]