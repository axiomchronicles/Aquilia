"""
Products Module - Services

Showcases:
- Pure Python Model ORM (Product, Review, ProductImage)
- In-memory product storage (simulating Model CRUD)
- Query-like filtering with Q-style patterns
- Effect-like transaction patterns
- @service with DI scoping
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from aquilia.di import service


@service(scope="app")
class ProductRepository:
    """
    Product data repository.

    In production, this would use Model.create / Model.query with a real database.
    Here we simulate ORM-powered CRUD with in-memory storage.
    """

    def __init__(self):
        self._products: Dict[str, Dict[str, Any]] = {}
        self._reviews: Dict[str, List[Dict[str, Any]]] = {}

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product (like Product.create)."""
        product_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        product = {
            "id": product_id,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "stock": 0,
            "currency": "USD",
            **data,
        }
        self._products[product_id] = product
        self._reviews[product_id] = []
        return product

    async def find_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Find product by ID (like Product.get(pk=...))."""
        product = self._products.get(product_id)
        if product:
            product["reviews"] = self._reviews.get(product_id, [])
        return product

    async def find_all(
        self,
        category: str = None,
        min_price: float = None,
        max_price: float = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Find products with filtering.

        Demonstrates Q-style query patterns:
        - Product.query().filter(category=category)
        - Product.query().filter(price__gte=min_price, price__lte=max_price)
        - Product.query().filter(is_active=True)
        """
        results = list(self._products.values())

        if active_only:
            results = [p for p in results if p.get("is_active", True)]
        if category:
            results = [p for p in results if p.get("category") == category]
        if min_price is not None:
            results = [p for p in results if p.get("price", 0) >= min_price]
        if max_price is not None:
            results = [p for p in results if p.get("price", 0) <= max_price]

        # Sort by created_at descending (like meta.ordering = ["-created_at"])
        results.sort(key=lambda p: p.get("created_at", ""), reverse=True)

        return results

    async def update(self, product_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update product (like product.save())."""
        if product_id not in self._products:
            return None
        self._products[product_id].update(data)
        self._products[product_id]["updated_at"] = datetime.now().isoformat()
        return self._products[product_id]

    async def delete(self, product_id: str) -> bool:
        """Delete product with cascade (removes reviews too)."""
        if product_id not in self._products:
            return False
        del self._products[product_id]
        self._reviews.pop(product_id, None)
        return True

    async def add_review(
        self,
        product_id: str,
        rating: int,
        comment: str,
        author: str,
    ) -> Optional[Dict[str, Any]]:
        """Add review to product (demonstrates linked model operations)."""
        if product_id not in self._products:
            return None
        review = {
            "id": str(uuid.uuid4()),
            "product_id": product_id,
            "rating": max(1, min(5, rating)),
            "comment": comment,
            "author_name": author,
            "created_at": datetime.now().isoformat(),
        }
        self._reviews[product_id].append(review)
        return review

    async def get_reviews(self, product_id: str) -> List[Dict[str, Any]]:
        """Get reviews for a product."""
        return self._reviews.get(product_id, [])

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search products by name/description.

        Demonstrates Product.query().filter(name__contains=query) style.
        """
        query_lower = query.lower()
        results = [
            p for p in self._products.values()
            if query_lower in p.get("name", "").lower()
            or query_lower in p.get("description", "").lower()
        ]
        return results

    async def update_stock(self, product_id: str, quantity: int) -> Optional[Dict[str, Any]]:
        """
        Adjust stock level.

        Demonstrates effect-like transactional operation.
        In production, wrap with DBTx for atomicity.
        """
        product = self._products.get(product_id)
        if not product:
            return None
        new_stock = product.get("stock", 0) + quantity
        if new_stock < 0:
            return None  # Insufficient stock
        product["stock"] = new_stock
        product["updated_at"] = datetime.now().isoformat()
        return product


@service(scope="app")
class ProductService:
    """
    Product business logic.

    Demonstrates constructor injection and business rule enforcement.
    """

    def __init__(self, repo: ProductRepository = None):
        self.repo = repo or ProductRepository()

    async def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create product with validation."""
        # Validate required fields
        required = ["name", "price", "sku", "category"]
        for field in required:
            if field not in data:
                return {"error": f"Missing required field: {field}"}

        # Validate price
        if data["price"] < 0:
            return {"error": "Price cannot be negative"}

        return await self.repo.create(data)

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return await self.repo.find_by_id(product_id)

    async def list_products(self, **filters) -> List[Dict[str, Any]]:
        return await self.repo.find_all(**filters)

    async def update_product(self, product_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Don't allow updating id or timestamps
        safe_data = {k: v for k, v in data.items() if k not in ("id", "created_at", "updated_at")}
        return await self.repo.update(product_id, safe_data)

    async def delete_product(self, product_id: str) -> bool:
        return await self.repo.delete(product_id)

    async def add_review(
        self,
        product_id: str,
        rating: int,
        comment: str,
        author: str,
    ) -> Optional[Dict[str, Any]]:
        return await self.repo.add_review(product_id, rating, comment, author)

    async def search_products(self, query: str) -> List[Dict[str, Any]]:
        return await self.repo.search(query)

    async def adjust_stock(self, product_id: str, quantity: int) -> Optional[Dict[str, Any]]:
        """Adjust stock with business rule validation."""
        return await self.repo.update_stock(product_id, quantity)
