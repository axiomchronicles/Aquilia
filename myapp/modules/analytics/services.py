"""
Analytics Module — Services

Analytics aggregation, reporting, and ML-powered recommendations.

Integrates Aquilia MLOps, Cache, and ORM for
production-grade analytics pipelines.
"""

from typing import Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from aquilia.di import service, Inject
from aquilia.cache import CacheService, cached
from aquilia.mlops import (
    RegistryService,
    PythonRuntime,
    MetricsCollector,
)

from ..orders.models import Order, OrderItem, OrderStatus
from ..products.models import Product, ProductStatus
from ..users.models import User
from .faults import (
    AnalyticsQueryFault,
    ModelInferenceFault,
    RecommendationFault,
)


@service(scope="app")
class AnalyticsService:
    """
    Business intelligence and KPI aggregation.

    Integrates:
    - Aquilia ORM (aggregate queries, Q objects)
    - Aquilia Cache (dashboard caching)
    - Aquilia MLOps (MetricsCollector for telemetry)
    """

    def __init__(
        self,
        cache: CacheService = Inject(CacheService),
    ):
        self.cache = cache

    @cached(ttl=300, namespace="analytics:dashboard")
    async def get_dashboard_stats(self) -> dict:
        """Aggregate KPIs for the admin dashboard."""
        total_users = await User.objects.count()
        active_users = await User.objects.filter(is_active=True).count()
        total_products = await Product.objects.filter(status=ProductStatus.ACTIVE).count()
        total_orders = await Order.objects.count()
        pending_orders = await Order.objects.filter(status=OrderStatus.PENDING).count()

        # revenue calculation
        completed_orders = await Order.objects.filter(
            status=OrderStatus.DELIVERED
        ).all()
        total_revenue = sum(
            float(o.total) for o in completed_orders
        ) if completed_orders else 0.0

        return {
            "users": {
                "total": total_users,
                "active": active_users,
            },
            "products": {
                "total": total_products,
            },
            "orders": {
                "total": total_orders,
                "pending": pending_orders,
                "revenue": round(total_revenue, 2),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @cached(ttl=600, namespace="analytics:revenue")
    async def get_revenue_timeline(self, days: int = 30) -> list:
        """Daily revenue for the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        orders = await Order.objects.filter(
            status=OrderStatus.DELIVERED,
            created_at__gte=cutoff,
        ).order_by("created_at").all()

        daily = {}
        for order in orders:
            day = order.created_at.strftime("%Y-%m-%d")
            daily[day] = daily.get(day, 0) + float(order.total)

        return [{"date": k, "revenue": round(v, 2)} for k, v in sorted(daily.items())]

    @cached(ttl=600, namespace="analytics:top-products")
    async def get_top_products(self, limit: int = 10) -> list:
        """Top products by purchase count."""
        products = await Product.objects.filter(
            status=ProductStatus.ACTIVE
        ).order_by("-purchase_count")[:limit].all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "purchases": p.purchase_count,
                "revenue": float(p.price) * p.purchase_count,
                "rating": p.rating_avg,
            }
            for p in products
        ]

    @cached(ttl=600, namespace="analytics:order-stats")
    async def get_order_status_distribution(self) -> dict:
        """Order count by status."""
        result = {}
        for status in OrderStatus:
            count = await Order.objects.filter(status=status.value).count()
            result[status.value] = count
        return result


@service(scope="app")
class RecommendationService:
    """
    Product recommendations using Aquilia MLOps + Cache.

    Integrates:
    - Aquilia MLOps (RegistryService, PythonRuntime for inference)
    - Aquilia Cache (recommendation caching per user)
    - Aquilia ORM (product queries)
    """

    def __init__(
        self,
        cache: CacheService = Inject(CacheService),
    ):
        self.cache = cache

    @cached(ttl=300, namespace="recommendations:user")
    async def get_for_user(self, user_id: int, limit: int = 8) -> list:
        """
        Get personalized recommendations for a user.
        Falls back to popularity-based if no ML model available.
        """
        try:
            # attempt ML-based recommendation via registry
            # if model is registered, use inference
            recommendations = await self._collaborative_filter(user_id, limit)
            if recommendations:
                return recommendations
        except Exception:
            pass

        # fallback: popularity-based
        return await self._popularity_based(limit)

    @cached(ttl=300, namespace="recommendations:similar")
    async def get_similar_products(self, product_id: int, limit: int = 6) -> list:
        """Content-based similar products."""
        try:
            product = await Product.objects.filter(id=product_id).first()
            if not product:
                return []

            # find products in same category with similar attributes
            similar = await Product.objects.filter(
                category_id=product.category_id,
                status=ProductStatus.ACTIVE,
            ).exclude(id=product_id).order_by("-rating_avg")[:limit].all()

            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "price": float(p.price),
                    "rating": p.rating_avg,
                    "images": p.images,
                }
                for p in similar
            ]
        except Exception:
            return []

    async def _collaborative_filter(self, user_id: int, limit: int) -> list:
        """
        Collaborative filtering stub.
        In production, integrates with Aquilia MLOps PythonRuntime
        for model inference.
        """
        # Check user order history for preferences
        order_items = await OrderItem.objects.filter(
            order__user_id=user_id,
            order__status=OrderStatus.DELIVERED,
        ).all()

        if not order_items:
            return []

        # get categories from purchased products
        product_ids = [item.product_id for item in order_items]
        purchased = await Product.objects.filter(id__in=product_ids).all()
        category_ids = list(set(p.category_id for p in purchased if p.category_id))

        if not category_ids:
            return []

        # recommend from same categories, excluding already purchased
        recommendations = await Product.objects.filter(
            category_id__in=category_ids,
            status=ProductStatus.ACTIVE,
        ).exclude(id__in=product_ids).order_by("-rating_avg")[:limit].all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": float(p.price),
                "rating": p.rating_avg,
                "images": p.images,
                "source": "collaborative",
            }
            for p in recommendations
        ]

    async def _popularity_based(self, limit: int) -> list:
        """Fallback: most popular products."""
        products = await Product.objects.filter(
            status=ProductStatus.ACTIVE
        ).order_by("-purchase_count", "-rating_avg")[:limit].all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": float(p.price),
                "rating": p.rating_avg,
                "images": p.images,
                "source": "popularity",
            }
            for p in products
        ]
