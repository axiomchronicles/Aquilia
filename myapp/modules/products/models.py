"""
Products Module — Models

Aquilia ORM models for product catalog, categories, reviews, and inventory.
"""

from aquilia.models import (
    Model,
    CharField,
    TextField,
    IntegerField,
    FloatField,
    DecimalField,
    BooleanField,
    DateTimeField,
    JSONField,
    SlugField,
    ForeignKey,
    ManyToManyField,
    Index,
    CASCADE,
    SET_NULL,
    PROTECT,
)
from aquilia.models.enums import TextChoices


class ProductStatus(TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
    OUT_OF_STOCK = "out_of_stock", "Out of Stock"


class Category(Model):
    """Product category with hierarchical support."""
    table = "categories"

    name = CharField(max_length=100)
    slug = SlugField(max_length=120, unique=True)
    description = TextField(null=True)
    parent = ForeignKey("Category", on_delete=CASCADE, null=True, related_name="children")
    image_url = CharField(max_length=500, null=True)
    sort_order = IntegerField(default=0)
    is_active = BooleanField(default=True)
    metadata = JSONField(default=dict)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [Index(fields=["slug"])]

    def __str__(self):
        return self.name


class Product(Model):
    """
    Core product model.

    Supports variants, categories, tags, and rich metadata.
    """
    table = "products"

    name = CharField(max_length=255)
    slug = SlugField(max_length=280, unique=True)
    sku = CharField(max_length=50, unique=True)
    description = TextField(null=True)
    short_description = CharField(max_length=500, null=True)
    price = DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = DecimalField(max_digits=10, decimal_places=2, null=True)
    cost_price = DecimalField(max_digits=10, decimal_places=2, null=True)
    currency = CharField(max_length=3, default="USD")
    category = ForeignKey("Category", on_delete=SET_NULL, null=True, related_name="products")
    vendor = ForeignKey("users.User", on_delete=CASCADE, related_name="products")
    status = CharField(max_length=20, default=ProductStatus.DRAFT)
    stock_quantity = IntegerField(default=0)
    low_stock_threshold = IntegerField(default=10)
    weight_grams = IntegerField(null=True)
    tags = JSONField(default=list)
    images = JSONField(default=list)
    attributes = JSONField(default=dict)
    is_featured = BooleanField(default=False)
    is_digital = BooleanField(default=False)
    rating_avg = FloatField(default=0.0)
    rating_count = IntegerField(default=0)
    view_count = IntegerField(default=0)
    purchase_count = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["slug"]),
            Index(fields=["sku"]),
            Index(fields=["category", "status"]),
            Index(fields=["vendor", "status"]),
            Index(fields=["status", "-created_at"]),
            Index(fields=["-rating_avg"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_on_sale(self) -> bool:
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.stock_quantity <= self.low_stock_threshold


class ProductReview(Model):
    """Customer product reviews with rating."""
    table = "product_reviews"

    product = ForeignKey("Product", on_delete=CASCADE, related_name="reviews")
    user = ForeignKey("users.User", on_delete=CASCADE, related_name="reviews")
    rating = IntegerField()  # 1-5
    title = CharField(max_length=200, null=True)
    body = TextField(null=True)
    is_verified_purchase = BooleanField(default=False)
    is_approved = BooleanField(default=False)
    helpful_count = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["product", "-rating"]),
            Index(fields=["user", "product"]),
        ]


class ProductVariant(Model):
    """Product variants (size, color, etc.)."""
    table = "product_variants"

    product = ForeignKey("Product", on_delete=CASCADE, related_name="variants")
    sku = CharField(max_length=50, unique=True)
    name = CharField(max_length=100)
    price_modifier = DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_quantity = IntegerField(default=0)
    attributes = JSONField(default=dict)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
