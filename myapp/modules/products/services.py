"""
Products Module — Services

Product catalog management with cache integration,
inventory tracking, and search capabilities.
"""

from typing import Optional
from datetime import datetime, timezone

from aquilia.di import service, Inject
from aquilia.cache import CacheService, cached, cache_aside, invalidate
from aquilia.models import Q, F

from .models import (
    Product,
    Category,
    ProductReview,
    ProductVariant,
    ProductStatus,
)
from .faults import (
    ProductNotFoundFault,
    CategoryNotFoundFault,
    DuplicateSkuFault,
    InsufficientStockFault,
    InvalidPriceFault,
)


@service(scope="app")
class CategoryService:
    """Category management with hierarchical tree support."""

    def __init__(self, cache: CacheService = Inject(CacheService)):
        self.cache = cache

    @cached(ttl=600, namespace="categories")
    async def list_categories(self, parent_id: Optional[int] = None) -> list:
        qs = Category.objects.filter(is_active=True)
        if parent_id is not None:
            qs = qs.filter(parent_id=parent_id)
        else:
            qs = qs.filter(parent__isnull=True)
        return await qs.all()

    @cached(ttl=600, namespace="categories")
    async def get_category(self, category_id: int) -> Category:
        cat = await Category.objects.filter(id=category_id).first()
        if not cat:
            raise CategoryNotFoundFault()
        return cat

    @cached(ttl=600, namespace="categories")
    async def get_by_slug(self, slug: str) -> Category:
        cat = await Category.objects.filter(slug=slug).first()
        if not cat:
            raise CategoryNotFoundFault()
        return cat

    @cached(ttl=600, namespace="categories:tree")
    async def get_category_tree(self) -> list:
        """Build the full category tree."""
        all_cats = await Category.objects.filter(is_active=True).all()
        lookup = {c.id: {**c.__dict__, "children": []} for c in all_cats}
        roots = []
        for c in all_cats:
            node = lookup[c.id]
            if c.parent_id and c.parent_id in lookup:
                lookup[c.parent_id]["children"].append(node)
            else:
                roots.append(node)
        return roots

    @invalidate(namespace="categories")
    async def create_category(self, data: dict) -> Category:
        slug = data.get("slug") or data["name"].lower().replace(" ", "-")
        cat = Category(slug=slug, **{k: v for k, v in data.items() if k != "slug"})
        await cat.save()
        return cat

    @invalidate(namespace="categories")
    async def update_category(self, category_id: int, data: dict) -> Category:
        cat = await self.get_category(category_id)
        for field, value in data.items():
            if hasattr(cat, field) and field not in ("id",):
                setattr(cat, field, value)
        await cat.save()
        return cat


@service(scope="app")
class ProductService:
    """
    Product catalog service with inventory, search, and caching.

    Integrates:
    - Aquilia Cache (@cached, @cache_aside, @invalidate)
    - Aquilia ORM (Q, F expressions, aggregation)
    - Aquilia Faults (domain-specific errors)
    """

    def __init__(
        self,
        cache: CacheService = Inject(CacheService),
        categories: CategoryService = Inject(CategoryService),
    ):
        self.cache = cache
        self.categories = categories

    # ── Queries ──────────────────────────────────────────────

    @cache_aside(ttl=300, namespace="products")
    async def get_by_id(self, product_id: int) -> Product:
        product = await Product.objects.filter(id=product_id).first()
        if not product:
            raise ProductNotFoundFault(str(product_id))
        return product

    @cached(ttl=300, namespace="products")
    async def get_by_slug(self, slug: str) -> Product:
        product = await Product.objects.filter(slug=slug).first()
        if not product:
            raise ProductNotFoundFault(slug)
        return product

    @cached(ttl=120, namespace="products:list")
    async def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        vendor_id: Optional[int] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_featured: Optional[bool] = None,
        sort_by: str = "-created_at",
        tags: Optional[list] = None,
    ) -> dict:
        qs = Product.objects.get_queryset()

        if category_id:
            qs = qs.filter(category_id=category_id)
        if status:
            qs = qs.filter(status=status)
        else:
            qs = qs.filter(status=ProductStatus.ACTIVE)
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(sku__icontains=search)
            )
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured)

        qs = qs.order_by(sort_by)
        total = await qs.count()
        offset = (page - 1) * page_size
        products = await qs[offset : offset + page_size].all()

        return {
            "items": products,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    @cached(ttl=600, namespace="products:featured")
    async def get_featured(self, limit: int = 12) -> list:
        return await Product.objects.filter(
            status=ProductStatus.ACTIVE, is_featured=True
        ).order_by("-rating_avg")[:limit].all()

    @cached(ttl=300, namespace="products:trending")
    async def get_trending(self, limit: int = 12) -> list:
        return await Product.objects.filter(
            status=ProductStatus.ACTIVE
        ).order_by("-purchase_count", "-view_count")[:limit].all()

    # ── Mutations ────────────────────────────────────────────

    @invalidate(namespace="products:list")
    async def create_product(self, data: dict, vendor_id: int) -> Product:
        if data.get("price", 0) <= 0:
            raise InvalidPriceFault()

        sku = data.get("sku", "")
        if await Product.objects.filter(sku=sku).exists():
            raise DuplicateSkuFault()

        slug = data.get("slug") or data["name"].lower().replace(" ", "-")
        product = Product(
            slug=slug,
            vendor_id=vendor_id,
            **{k: v for k, v in data.items() if k != "slug"},
        )
        await product.save()
        return product

    @invalidate(namespace="products")
    async def update_product(self, product_id: int, data: dict) -> Product:
        product = await self.get_by_id(product_id)
        for field, value in data.items():
            if hasattr(product, field) and field not in ("id", "sku", "slug", "vendor_id"):
                setattr(product, field, value)
        await product.save()
        return product

    @invalidate(namespace="products")
    async def increment_view_count(self, product_id: int) -> None:
        await Product.objects.filter(id=product_id).update(
            view_count=F("view_count") + 1
        )

    # ── Inventory ────────────────────────────────────────────

    async def check_stock(self, product_id: int, quantity: int) -> bool:
        product = await self.get_by_id(product_id)
        return product.stock_quantity >= quantity

    @invalidate(namespace="products")
    async def reserve_stock(self, product_id: int, quantity: int) -> None:
        product = await self.get_by_id(product_id)
        if product.stock_quantity < quantity:
            raise InsufficientStockFault(
                product.name, product.stock_quantity, quantity
            )
        await Product.objects.filter(id=product_id).update(
            stock_quantity=F("stock_quantity") - quantity
        )

    @invalidate(namespace="products")
    async def release_stock(self, product_id: int, quantity: int) -> None:
        await Product.objects.filter(id=product_id).update(
            stock_quantity=F("stock_quantity") + quantity
        )

    # ── Reviews ──────────────────────────────────────────────

    @cached(ttl=300, namespace="reviews")
    async def get_reviews(
        self, product_id: int, page: int = 1, page_size: int = 10
    ) -> dict:
        qs = ProductReview.objects.filter(
            product_id=product_id, is_approved=True
        ).order_by("-created_at")
        total = await qs.count()
        offset = (page - 1) * page_size
        reviews = await qs[offset : offset + page_size].all()
        return {
            "items": reviews,
            "total": total,
            "page": page,
            "pages": (total + page_size - 1) // page_size,
        }

    @invalidate(namespace="reviews")
    async def add_review(
        self, product_id: int, user_id: int, data: dict
    ) -> ProductReview:
        review = ProductReview(
            product_id=product_id,
            user_id=user_id,
            **data,
        )
        await review.save()

        # recalculate product rating
        reviews = await ProductReview.objects.filter(product_id=product_id).all()
        if reviews:
            total_rating = sum(r.rating for r in reviews)
            count = len(reviews)
            await Product.objects.filter(id=product_id).update(
                rating_avg=total_rating / count,
                rating_count=count,
            )

        return review
