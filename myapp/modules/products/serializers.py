"""
Products Module — Serializers

ModelSerializer with nested relations, computed fields,
and filtering-aware list serializers.
"""

from aquilia.serializers import (
    Serializer,
    ModelSerializer,
    ListSerializer,
    CharField,
    IntegerField,
    FloatField,
    DecimalField,
    BooleanField,
    DateTimeField,
    JSONField,
    SlugRelatedField,
    PrimaryKeyRelatedField,
)

from .models import Product, Category, ProductReview, ProductVariant


# ─── Category Serializers ─────────────────────────────────────

class CategorySerializer(ModelSerializer):
    """Category with nested children count."""
    product_count = IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description",
            "parent", "image_url", "sort_order",
            "is_active", "product_count", "metadata",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class CategoryTreeSerializer(ModelSerializer):
    """Category with recursive children for tree rendering."""
    children = ListSerializer(child=CategorySerializer())

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description",
            "image_url", "sort_order", "is_active",
            "children",
        ]


# ─── Review Serializers ──────────────────────────────────────

class ProductReviewSerializer(ModelSerializer):
    """Product review with author username."""
    author_username = CharField(read_only=True, source="user.username")

    class Meta:
        model = ProductReview
        fields = [
            "id", "rating", "title", "body",
            "author_username", "is_verified_purchase",
            "helpful_count", "created_at",
        ]
        read_only_fields = [
            "id", "author_username", "is_verified_purchase",
            "helpful_count", "created_at",
        ]


class ProductReviewCreateSerializer(ModelSerializer):
    """Validates review creation."""
    class Meta:
        model = ProductReview
        fields = ["rating", "title", "body"]

    def validate_rating(self, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return value


# ─── Variant Serializers ─────────────────────────────────────

class ProductVariantSerializer(ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", "name", "price_modifier",
            "stock_quantity", "attributes", "is_active",
        ]
        read_only_fields = ["id"]


# ─── Product Serializers ─────────────────────────────────────

class ProductListSerializer(ModelSerializer):
    """Compact product view for listings/search results."""
    category_name = CharField(read_only=True, source="category.name")
    is_on_sale = BooleanField(read_only=True)
    in_stock = BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "sku",
            "short_description", "price", "compare_at_price",
            "currency", "category_name", "status",
            "is_featured", "is_on_sale", "in_stock",
            "rating_avg", "rating_count",
            "images", "tags",
            "created_at",
        ]
        read_only_fields = [
            "id", "slug", "rating_avg", "rating_count",
            "created_at",
        ]


class ProductDetailSerializer(ModelSerializer):
    """Full product detail with nested variants and reviews."""
    category = CategorySerializer(read_only=True)
    variants = ListSerializer(child=ProductVariantSerializer())
    recent_reviews = ListSerializer(child=ProductReviewSerializer())
    is_on_sale = BooleanField(read_only=True)
    in_stock = BooleanField(read_only=True)
    is_low_stock = BooleanField(read_only=True)
    vendor_username = CharField(read_only=True, source="vendor.username")

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "sku",
            "description", "short_description",
            "price", "compare_at_price", "cost_price", "currency",
            "category", "vendor_username",
            "status", "stock_quantity",
            "is_featured", "is_digital", "is_on_sale",
            "in_stock", "is_low_stock",
            "weight_grams", "tags", "images", "attributes",
            "rating_avg", "rating_count",
            "view_count", "purchase_count",
            "variants", "recent_reviews",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "rating_avg", "rating_count",
            "view_count", "purchase_count",
            "created_at", "updated_at",
        ]


class ProductCreateSerializer(ModelSerializer):
    """Validates product creation with required business fields."""
    class Meta:
        model = Product
        fields = [
            "name", "sku", "description", "short_description",
            "price", "compare_at_price", "cost_price", "currency",
            "category", "status", "stock_quantity",
            "low_stock_threshold", "weight_grams",
            "tags", "images", "attributes",
            "is_featured", "is_digital",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise ValueError("Price must be greater than zero")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise ValueError("Stock quantity cannot be negative")
        return value


class ProductUpdateSerializer(ModelSerializer):
    """Validates product update (partial update)."""
    class Meta:
        model = Product
        fields = [
            "name", "description", "short_description",
            "price", "compare_at_price", "cost_price",
            "category", "status", "stock_quantity",
            "low_stock_threshold", "weight_grams",
            "tags", "images", "attributes",
            "is_featured", "is_digital",
        ]
