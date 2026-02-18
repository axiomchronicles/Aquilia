"""
Products Module — Product catalog, categories, reviews, and inventory.

Components:
- Models: Product, Category, ProductReview, ProductVariant
- Services: ProductService, CategoryService
- Controllers: ProductController, CategoryController
- Serializers: Full CRUD with nested relations
- Faults: Product-specific error handling
"""

from .models import Product, Category, ProductReview, ProductVariant, ProductStatus
from .services import ProductService, CategoryService
from .controllers import ProductController, CategoryController
from .faults import (
    ProductNotFoundFault,
    CategoryNotFoundFault,
    InsufficientStockFault,
)

__all__ = [
    "Product", "Category", "ProductReview", "ProductVariant", "ProductStatus",
    "ProductService", "CategoryService",
    "ProductController", "CategoryController",
    "ProductNotFoundFault", "CategoryNotFoundFault", "InsufficientStockFault",
]
