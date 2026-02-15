"""
Products Module - Services

Showcases:
- Pure Python Model ORM (Product, Review, ProductImage)
- Real database operations using Aquilia ORM
- Query-like filtering with Q-style patterns
- Effect-like transaction patterns
- @service with DI scoping
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from aquilia.di import service
from .models import Product, Review


@service(scope="app")
class ProductRepository:
    """
    Product data repository using Aquilia ORM.
    
    Demonstrates real database operations with Product and Review models.
    """

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product using the ORM."""
        product = await Product.create(**data)
        return product.to_dict()

    async def find_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Find product by ID with related reviews."""
        product = await Product.get(id=product_id)
        if not product:
            return None
        
        # Get reviews for this product
        reviews = await Review.query().filter(product_id=product_id).all()
        
        result = product.to_dict()
        result["reviews"] = [r.to_dict() for r in reviews]
        return result

    async def find_all(
        self,
        category: str = None,
        min_price: float = None,
        max_price: float = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Find products with filtering using ORM queries.
        
        Demonstrates:
        - Product.query().filter(category=category)
        - Product.query().filter(price__gte=min_price, price__lte=max_price)
        - Product.query().filter(is_active=True)
        """
        query = Product.query()
        
        if active_only:
            query = query.filter(is_active=True)
        if category:
            query = query.filter(category=category)
        if min_price is not None:
            query = query.filter(price__gte=min_price)
        if max_price is not None:
            query = query.filter(price__lte=max_price)
        
        # Order by created_at descending (already in Meta.ordering)
        products = await query.all()
        return [p.to_dict() for p in products]

    async def update(self, product_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update product using ORM."""
        product = await Product.get(id=product_id)
        if not product:
            return None
        
        # Update fields
        for key, value in data.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        await product.save()
        return product.to_dict()

    async def delete(self, product_id: int) -> bool:
        """Delete product (CASCADE will handle reviews)."""
        product = await Product.get(id=product_id)
        if not product:
            return False
        
        await product.delete()
        return True

    async def add_review(
        self,
        product_id: int,
        rating: int,
        comment: str,
        author: str,
    ) -> Optional[Dict[str, Any]]:
        """Add review to product using Review model."""
        product = await Product.get(id=product_id)
        if not product:
            return None
        
        review = await Review.create(
            product_id=product_id,
            rating=max(1, min(5, rating)),
            comment=comment,
            author_name=author,
        )
        return review.to_dict()

    async def get_reviews(self, product_id: int) -> List[Dict[str, Any]]:
        """Get reviews for a product."""
        reviews = await Review.query().filter(product_id=product_id).all()
        return [r.to_dict() for r in reviews]

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search products by name/description.
        
        Demonstrates Product.query().filter(name__contains=query).
        """
        products = await Product.query().filter(name__icontains=query).all()
        return [p.to_dict() for p in products]

    async def update_stock(self, product_id: int, quantity: int) -> Optional[Dict[str, Any]]:
        """
        Adjust stock level.
        
        Demonstrates transactional operation with validation.
        """
        product = await Product.get(id=product_id)
        if not product:
            return None
        
        new_stock = product.stock + quantity
        if new_stock < 0:
            return None  # Insufficient stock
        
        product.stock = new_stock
        await product.save()
        return product.to_dict()


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

    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        return await self.repo.find_by_id(product_id)

    async def list_products(self, **filters) -> List[Dict[str, Any]]:
        return await self.repo.find_all(**filters)

    async def update_product(self, product_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Don't allow updating id or timestamps
        safe_data = {k: v for k, v in data.items() if k not in ("id", "created_at", "updated_at")}
        return await self.repo.update(product_id, safe_data)

    async def delete_product(self, product_id: int) -> bool:
        return await self.repo.delete(product_id)

    async def add_review(
        self,
        product_id: int,
        rating: int,
        comment: str,
        author: str,
    ) -> Optional[Dict[str, Any]]:
        return await self.repo.add_review(product_id, rating, comment, author)

    async def search_products(self, query: str) -> List[Dict[str, Any]]:
        return await self.repo.search(query)

    async def adjust_stock(self, product_id: int, quantity: int) -> Optional[Dict[str, Any]]:
        """Adjust stock with business rule validation."""
        return await self.repo.update_stock(product_id, quantity)
