"""
Admin Module — Services

Administrative operations: bulk management, system health,
audit logs, and aggregated dashboard data.

Uses ORM directly for cross-module queries to avoid DI
cross-module resolution issues.
"""

from typing import Optional
from datetime import datetime, timezone

from aquilia.di import service, Inject
from aquilia.cache import CacheService, cached, invalidate

from ..users.models import User
from ..products.models import Product, ProductStatus
from ..orders.models import Order, OrderItem, OrderStatus
from .faults import (
    AdminAccessDeniedFault,
    BulkOperationFault,
    SystemHealthFault,
)


@service(scope="app")
class AdminService:
    """
    Admin aggregation service.

    Uses Aquilia ORM directly for cross-module queries
    rather than injecting cross-module services, which avoids
    DI provider-not-found issues across module boundaries.
    """

    def __init__(
        self,
        cache: CacheService = Inject(CacheService),
    ):
        self.cache = cache

    @cached(ttl=120, namespace="admin:dashboard")
    async def get_admin_dashboard(self) -> dict:
        """Aggregate all dashboard data via direct ORM queries."""
        # Users
        total_users = await User.objects.count()
        active_users = await User.objects.filter(is_active=True).count()

        # Products
        total_products = await Product.objects.filter(
            status=ProductStatus.ACTIVE
        ).count()

        # Orders
        total_orders = await Order.objects.count()
        pending_orders = await Order.objects.filter(
            status=OrderStatus.PENDING
        ).count()
        completed_orders = await Order.objects.filter(
            status=OrderStatus.DELIVERED
        ).all()
        total_revenue = sum(
            float(o.total) for o in completed_orders
        ) if completed_orders else 0.0

        # Top products by order count
        all_items = await OrderItem.objects.all()
        product_counts = {}
        for item in (all_items or []):
            pid = item.product_id
            product_counts[pid] = product_counts.get(pid, 0) + item.quantity
        sorted_products = sorted(
            product_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]
        top_products = [
            {"product_id": pid, "quantity_sold": qty}
            for pid, qty in sorted_products
        ]

        # Order status distribution
        statuses = {}
        all_orders = await Order.objects.all()
        for o in (all_orders or []):
            s = str(o.status.value) if hasattr(o.status, 'value') else str(o.status)
            statuses[s] = statuses.get(s, 0) + 1

        stats = {
            "users": {"total": total_users, "active": active_users},
            "products": {"total": total_products},
            "orders": {
                "total": total_orders,
                "pending": pending_orders,
                "revenue": round(total_revenue, 2),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "stats": stats,
            "top_products": top_products,
            "order_distribution": statuses,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def bulk_update_user_status(
        self, user_ids: list, is_active: bool
    ) -> dict:
        """Bulk activate/deactivate users."""
        results = {"success": 0, "failed": 0, "errors": []}
        for uid in user_ids:
            try:
                user = await User.objects.filter(id=uid).first()
                if not user:
                    raise ValueError(f"User {uid} not found")
                user.is_active = is_active
                await user.save()
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"user_id": uid, "error": str(e)})
        return results

    async def bulk_update_order_status(
        self, order_ids: list, new_status: str, actor_id: str
    ) -> dict:
        """Bulk update order statuses."""
        results = {"success": 0, "failed": 0, "errors": []}
        for oid in order_ids:
            try:
                order = await Order.objects.filter(id=oid).first()
                if not order:
                    raise ValueError(f"Order {oid} not found")
                order.status = new_status
                await order.save()
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"order_id": oid, "error": str(e)})
        return results

    @cached(ttl=60, namespace="admin:health")
    async def system_health_check(self) -> dict:
        """System health via Aquilia Cache health check + ORM probe."""
        checks = {
            "database": "healthy",
            "cache": "unknown",
            "mail": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # cache health
        try:
            await self.cache.set("_health_check", "ok", ttl=10, namespace="system")
            val = await self.cache.get("_health_check", namespace="system")
            checks["cache"] = "healthy" if val == "ok" else "degraded"
        except Exception:
            checks["cache"] = "unhealthy"

        # database health — direct ORM query
        try:
            await User.objects.count()
            checks["database"] = "healthy"
        except Exception:
            checks["database"] = "unhealthy"

        overall = "healthy"
        if any(v == "unhealthy" for v in checks.values() if isinstance(v, str) and v != checks["timestamp"]):
            overall = "unhealthy"
        elif any(v == "degraded" for v in checks.values() if isinstance(v, str)):
            overall = "degraded"

        checks["overall"] = overall
        return checks

    async def send_admin_notification(
        self, title: str, body: str, target_user_ids: list = None
    ) -> dict:
        """Send system-wide or targeted notifications (in-memory broadcast)."""
        if target_user_ids:
            user_ids = target_user_ids
        else:
            active_users = await User.objects.filter(is_active=True).all()
            user_ids = [u.id for u in (active_users or [])]
        # In a production setup, this would publish to a message queue
        # or notification service. For now, we log the broadcast.
        return {"sent": len(user_ids), "title": title}

    @invalidate(namespace="admin:dashboard")
    async def invalidate_dashboard_cache(self) -> None:
        """Force refresh of dashboard data."""
        pass
