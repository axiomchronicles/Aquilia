"""
Products Module - Pure Python Models

Showcases the Aquilia ORM with Django-grade field types,
relationships, indexes, and meta options.
"""

from aquilia.models import Model
from aquilia.models.fields import (
    CharField,
    DateTimeField,
    FloatField,
    IntegerField,
    TextField,
    BooleanField,
    SlugField,
    UUIDField,
    ForeignKey,
    Index,
    UniqueConstraint,
)


class Product(Model):
    """Core product model for the e-commerce catalog."""

    table = "products"

    name = CharField(max_length=200)
    description = TextField(null=True)
    price = FloatField(default=0.0)
    currency = CharField(max_length=3, default="USD")
    sku = SlugField(max_length=100, unique=True)
    stock = IntegerField(default=0)
    category = CharField(max_length=100)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["category", "is_active"]),
            Index(fields=["price"]),
        ]
        constraints = [
            UniqueConstraint(fields=["sku"]),
        ]


class Review(Model):
    """Product review with 1-5 star rating."""

    table = "reviews"

    product = ForeignKey("Product", related_name="reviews", on_delete="CASCADE")
    rating = IntegerField()
    comment = TextField(null=True)
    author_name = CharField(max_length=150)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ProductImage(Model):
    """Product image with sort ordering."""

    table = "product_images"

    product = ForeignKey("Product", related_name="images", on_delete="CASCADE")
    url = CharField(max_length=500)
    alt_text = CharField(max_length=200, null=True)
    sort_order = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order"]
