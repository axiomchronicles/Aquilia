"""
Products Module — Controllers

Full REST API for product catalog, categories, reviews, and variants.

Integrates:
- Aquilia Controller with prefix/tags
- Aquilia Route Decorators (@GET, @POST, @PUT, @DELETE, @PATCH)
- Aquilia RequestCtx (request, identity, session, container)
- Aquilia Response (JSON with caching headers)
- Aquilia Serializers (input validation, output shaping)
- Aquilia Cache (response caching via service layer)
"""

from aquilia.controller import Controller
from aquilia.controller.decorators import GET, POST, PUT, DELETE, PATCH
from aquilia.engine import RequestCtx
from aquilia.response import Response

from .services import ProductService, CategoryService
from .serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    CategorySerializer,
    CategoryTreeSerializer,
    ProductReviewSerializer,
    ProductReviewCreateSerializer,
    ProductVariantSerializer,
)
from .faults import ProductNotFoundFault
from ..users.faults import InsufficientPermissionsFault


class CategoryController(Controller):
    """Category CRUD and tree endpoints."""
    prefix = "/categories"
    tags = ["Categories"]

    def __init__(self, category_service: CategoryService = None):
        self.categories = category_service

    @GET("/")
    async def list_categories(self, ctx: RequestCtx) -> Response:
        """List root categories."""
        service = await ctx.container.resolve_async(CategoryService)
        parent_id = ctx.request.query_params.get("parent_id")
        categories = await service.list_categories(
            parent_id=int(parent_id) if parent_id else None
        )
        serializer = CategorySerializer.many(instance=categories)
        return Response.json(serializer.data)

    @GET("/tree")
    async def category_tree(self, ctx: RequestCtx) -> Response:
        """Full category hierarchy tree."""
        service = await ctx.container.resolve_async(CategoryService)
        tree = await service.get_category_tree()
        return Response.json(tree)

    @GET("/«category_id:int»")
    async def get_category(self, ctx: RequestCtx, category_id: int) -> Response:
        service = await ctx.container.resolve_async(CategoryService)
        category = await service.get_category(category_id)
        serializer = CategorySerializer(instance=category)
        return Response.json(serializer.data)

    @GET("/slug/«slug»")
    async def get_by_slug(self, ctx: RequestCtx, slug: str) -> Response:
        service = await ctx.container.resolve_async(CategoryService)
        category = await service.get_by_slug(slug)
        serializer = CategorySerializer(instance=category)
        return Response.json(serializer.data)

    @POST("/")
    async def create_category(self, ctx: RequestCtx) -> Response:
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        serializer = await CategorySerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        service = await ctx.container.resolve_async(CategoryService)
        category = await service.create_category(serializer.validated_data)
        result = CategorySerializer(instance=category)
        return Response.json(result.data, status=201)

    @PUT("/«category_id:int»")
    async def update_category(self, ctx: RequestCtx, category_id: int) -> Response:
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        serializer = await CategorySerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        service = await ctx.container.resolve_async(CategoryService)
        category = await service.update_category(category_id, serializer.validated_data)
        result = CategorySerializer(instance=category)
        return Response.json(result.data)


class ProductController(Controller):
    """
    Product catalog endpoints with advanced filtering,
    pagination, search, and variant management.
    """
    prefix = "/products"
    tags = ["Products"]

    def __init__(self, product_service: ProductService = None):
        self.products = product_service

    # ── Listings ─────────────────────────────────────────────

    @GET("/")
    async def list_products(self, ctx: RequestCtx) -> Response:
        """
        List products with filtering, search, and pagination.

        Query params: page, page_size, category_id, status,
        search, min_price, max_price, is_featured, sort_by
        """
        params = ctx.request.query_params
        service = await ctx.container.resolve_async(ProductService)

        result = await service.list_products(
            page=int(params.get("page", 1)),
            page_size=int(params.get("page_size", 20)),
            category_id=int(params["category_id"]) if "category_id" in params else None,
            status=params.get("status"),
            search=params.get("search"),
            min_price=float(params["min_price"]) if "min_price" in params else None,
            max_price=float(params["max_price"]) if "max_price" in params else None,
            is_featured=params.get("is_featured") == "true" if "is_featured" in params else None,
            sort_by=params.get("sort_by", "-created_at"),
        )

        serializer = ProductListSerializer.many(instance=result["items"])
        return Response.json({
            "items": serializer.data,
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "pages": result["pages"],
        })

    @GET("/featured")
    async def featured_products(self, ctx: RequestCtx) -> Response:
        """Featured products for homepage."""
        service = await ctx.container.resolve_async(ProductService)
        limit = int(ctx.request.query_params.get("limit", 12))
        products = await service.get_featured(limit=limit)
        serializer = ProductListSerializer.many(instance=products)
        return Response.json(serializer.data)

    @GET("/trending")
    async def trending_products(self, ctx: RequestCtx) -> Response:
        """Trending products by purchase volume."""
        service = await ctx.container.resolve_async(ProductService)
        limit = int(ctx.request.query_params.get("limit", 12))
        products = await service.get_trending(limit=limit)
        serializer = ProductListSerializer.many(instance=products)
        return Response.json(serializer.data)

    # ── Detail ───────────────────────────────────────────────

    @GET("/«product_id:int»")
    async def get_product(self, ctx: RequestCtx, product_id: int) -> Response:
        """Get full product detail with variants and reviews."""
        service = await ctx.container.resolve_async(ProductService)
        product = await service.get_by_id(product_id)

        # track view asynchronously
        await service.increment_view_count(product_id)

        serializer = ProductDetailSerializer(instance=product)
        return Response.json(serializer.data)

    @GET("/slug/«slug»")
    async def get_by_slug(self, ctx: RequestCtx, slug: str) -> Response:
        service = await ctx.container.resolve_async(ProductService)
        product = await service.get_by_slug(slug)
        await service.increment_view_count(product.id)
        serializer = ProductDetailSerializer(instance=product)
        return Response.json(serializer.data)

    # ── CRUD (Vendor/Admin) ──────────────────────────────────

    @POST("/")
    async def create_product(self, ctx: RequestCtx) -> Response:
        """Create a new product (vendor or admin)."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        serializer = await ProductCreateSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        service = await ctx.container.resolve_async(ProductService)
        product = await service.create_product(
            data=serializer.validated_data,
            vendor_id=int(ctx.identity.id),
        )
        result = ProductDetailSerializer(instance=product)
        return Response.json(result.data, status=201)

    @PUT("/«product_id:int»")
    async def update_product(self, ctx: RequestCtx, product_id: int) -> Response:
        """Update product (owner or admin)."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        serializer = await ProductUpdateSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        service = await ctx.container.resolve_async(ProductService)
        product = await service.update_product(product_id, serializer.validated_data)
        result = ProductDetailSerializer(instance=product)
        return Response.json(result.data)

    # ── Reviews ──────────────────────────────────────────────

    @GET("/«product_id:int»/reviews")
    async def list_reviews(self, ctx: RequestCtx, product_id: int) -> Response:
        """List product reviews with pagination."""
        params = ctx.request.query_params
        service = await ctx.container.resolve_async(ProductService)
        result = await service.get_reviews(
            product_id,
            page=int(params.get("page", 1)),
            page_size=int(params.get("page_size", 10)),
        )
        serializer = ProductReviewSerializer.many(instance=result["items"])
        return Response.json({
            "items": serializer.data,
            "total": result["total"],
            "page": result["page"],
            "pages": result["pages"],
        })

    @POST("/«product_id:int»/reviews")
    async def add_review(self, ctx: RequestCtx, product_id: int) -> Response:
        """Add a product review (authenticated users)."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        serializer = await ProductReviewCreateSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        service = await ctx.container.resolve_async(ProductService)
        review = await service.add_review(
            product_id,
            user_id=int(ctx.identity.id),
            data=serializer.validated_data,
        )
        result = ProductReviewSerializer(instance=review)
        return Response.json(result.data, status=201)

    # ── Stock Check ──────────────────────────────────────────

    @GET("/«product_id:int»/stock")
    async def check_stock(self, ctx: RequestCtx, product_id: int) -> Response:
        """Check product stock availability."""
        service = await ctx.container.resolve_async(ProductService)
        product = await service.get_by_id(product_id)
        return Response.json({
            "product_id": product.id,
            "sku": product.sku,
            "stock_quantity": product.stock_quantity,
            "in_stock": product.in_stock,
            "is_low_stock": product.is_low_stock,
        })
