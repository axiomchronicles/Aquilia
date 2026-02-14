"""
Products Module - Controllers

Showcases:
- Full CRUD with pattern-based routing («id:uuid», «slug:slug»)
- Query parameter filtering
- Nested resource routes (reviews)
- Search endpoint
- Stock management
- Pure Python Model ORM awareness
"""

from aquilia import Controller, GET, POST, PUT, DELETE, PATCH, RequestCtx, Response
from .services import ProductService
from .faults import ProductNotFoundFault, InvalidProductDataFault, InsufficientStockFault


class ProductsController(Controller):
    """
    Products API controller.

    Demonstrates:
    - Complex pattern-based routing
    - Query parameter extraction
    - Nested resources (reviews)
    - Stock management endpoints
    """

    prefix = "/"
    tags = ["products", "catalog"]

    def __init__(self, service: ProductService = None):
        self.service = service or ProductService()

    # ── Product CRUD ─────────────────────────────────────────────────────

    @GET("/")
    async def list_products(self, ctx: RequestCtx):
        """
        List products with optional filtering.

        GET /products/?category=electronics&min_price=10&max_price=500

        Demonstrates query parameter extraction from RequestCtx.
        """
        params = ctx.query_params
        filters = {}

        if "category" in params:
            filters["category"] = params["category"]
        if "min_price" in params:
            filters["min_price"] = float(params["min_price"])
        if "max_price" in params:
            filters["max_price"] = float(params["max_price"])

        products = await self.service.list_products(**filters)
        return Response.json({
            "items": products,
            "total": len(products),
            "filters": filters,
        })

    @POST("/")
    async def create_product(self, ctx: RequestCtx):
        """
        Create a new product.

        POST /products/
        Body: {"name": "...", "price": 29.99, "sku": "SKU001", "category": "electronics"}
        """
        data = await ctx.json()
        result = await self.service.create_product(data)

        if "error" in result:
            raise InvalidProductDataFault(result["error"])

        return Response.json(result, status=201)

    @GET("/«id:str»")
    async def get_product(self, ctx: RequestCtx, id: str):
        """
        Get product by ID.

        GET /products/<id>
        Uses «id:str» pattern for UUID string matching.
        """
        product = await self.service.get_product(id)
        if not product:
            raise ProductNotFoundFault(id)
        return Response.json(product)

    @PUT("/«id:str»")
    async def update_product(self, ctx: RequestCtx, id: str):
        """
        Update product.

        PUT /products/<id>
        Body: {"name": "Updated Name", "price": 39.99}
        """
        data = await ctx.json()
        updated = await self.service.update_product(id, data)
        if not updated:
            raise ProductNotFoundFault(id)
        return Response.json(updated)

    @DELETE("/«id:str»")
    async def delete_product(self, ctx: RequestCtx, id: str):
        """
        Delete product (cascades to reviews).

        DELETE /products/<id>
        """
        deleted = await self.service.delete_product(id)
        if not deleted:
            raise ProductNotFoundFault(id)
        return Response.json({"deleted": True, "id": id})

    # ── Search ───────────────────────────────────────────────────────────

    @GET("/search")
    async def search(self, ctx: RequestCtx):
        """
        Search products by name/description.

        GET /products/search?q=laptop

        Demonstrates Product.query().filter(name__contains=...) style search.
        """
        query = ctx.query_params.get("q", "")
        if not query:
            return Response.json({"error": "Query parameter 'q' is required"}, status=400)

        results = await self.service.search_products(query)
        return Response.json({
            "query": query,
            "items": results,
            "total": len(results),
        })

    # ── Stock Management ────────────────────────────────────────────────

    @PATCH("/«id:str»/stock")
    async def adjust_stock(self, ctx: RequestCtx, id: str):
        """
        Adjust product stock level.

        PATCH /products/<id>/stock
        Body: {"quantity": 10}  or  {"quantity": -5}

        Demonstrates effect-like transactional operation with Model ORM.
        """
        data = await ctx.json()
        quantity = data.get("quantity", 0)

        result = await self.service.adjust_stock(id, quantity)
        if not result:
            # Could be product not found OR insufficient stock
            product = await self.service.get_product(id)
            if not product:
                raise ProductNotFoundFault(id)
            raise InsufficientStockFault(id, abs(quantity), product.get("stock", 0))

        return Response.json({
            "id": id,
            "stock": result["stock"],
            "adjusted_by": quantity,
        })

    # ── Reviews (Nested Resource) ───────────────────────────────────────

    @GET("/«id:str»/reviews")
    async def list_reviews(self, ctx: RequestCtx, id: str):
        """
        List reviews for a product.

        GET /products/<id>/reviews

        Demonstrates nested resource routing.
        """
        product = await self.service.get_product(id)
        if not product:
            raise ProductNotFoundFault(id)

        reviews = product.get("reviews", [])
        return Response.json({
            "product_id": id,
            "reviews": reviews,
            "total": len(reviews),
            "average_rating": (
                sum(r["rating"] for r in reviews) / len(reviews)
                if reviews else 0
            ),
        })

    @POST("/«id:str»/reviews")
    async def add_review(self, ctx: RequestCtx, id: str):
        """
        Add review to a product.

        POST /products/<id>/reviews
        Body: {"rating": 5, "comment": "Great product!", "author": "John"}
        """
        data = await ctx.json()
        rating = data.get("rating", 0)
        comment = data.get("comment", "")
        author = data.get("author", "Anonymous")

        if not (1 <= rating <= 5):
            return Response.json(
                {"error": "Rating must be between 1 and 5"},
                status=400,
            )

        review = await self.service.add_review(id, rating, comment, author)
        if not review:
            raise ProductNotFoundFault(id)

        return Response.json(review, status=201)
