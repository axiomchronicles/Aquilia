"""
Analytics Service — Dashboard aggregation with caching.
Fully wired through the Aquilia ORM — no raw SQL.
Uses ORM aggregate, annotate, group_by, values, filter, exclude, where.
"""

from typing import Dict, Any, List
from aquilia.di import service
from aquilia.cache import CacheService, cached

from aquilia.models import Count, Sum, Coalesce, Value, F, Case, When

from modules.shared.models import Contact, Company, Deal, Task, Activity, User


@service(scope="app")
class AnalyticsService:
    """Aggregates dashboard data from all CRM entities."""

    def __init__(self, cache: CacheService = None):
        self.cache = cache

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Aggregate all dashboard metrics."""
        cache_key = "dashboard:main"
        if self.cache:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data

        data = {
            "kpis": await self._get_kpis(),
            "pipeline": await self._get_pipeline_summary(),
            "recent_activities": await self._get_recent_activities(),
            "tasks_overview": await self._get_tasks_overview(),
            "revenue_by_stage": await self._get_revenue_by_stage(),
            "contacts_by_status": await self._get_contacts_by_status(),
            "top_deals": await self._get_top_deals(),
            "team_performance": await self._get_team_performance(),
        }

        if self.cache:
            await self.cache.set(cache_key, data, ttl=60)

        return data

    async def _get_kpis(self) -> Dict[str, Any]:
        """Key Performance Indicators — pure ORM counts + aggregates."""
        # Simple counts via ORM
        total_contacts = await Contact.objects.count()
        total_companies = await Company.objects.count()
        total_deals = await Deal.objects.count()

        # Filtered counts and aggregates via ORM
        active_deals = await Deal.objects.exclude(
            stage__in=["closed_won", "closed_lost"]
        ).count()

        pipeline_value_result = await (
            Deal.objects.exclude(stage__in=["closed_won", "closed_lost"])
            .aggregate(total=Coalesce(Sum("value"), Value(0)))
        )

        won_value_result = await (
            Deal.objects.filter(stage="closed_won")
            .aggregate(total=Coalesce(Sum("value"), Value(0)))
        )

        won_count = await Deal.objects.filter(stage="closed_won").count()

        total_closed = await Deal.objects.filter(
            stage__in=["closed_won", "closed_lost"]
        ).count()

        open_tasks = await Task.objects.filter(
            status__in=["pending", "in_progress"]
        ).count()

        overdue_tasks = await (
            Task.query()
            .where("due_date < datetime('now')")
            .exclude(status__in=["completed", "cancelled"])
            .count()
        )

        # Win rate: won / total closed, avoid division by zero
        win_rate = (won_count / total_closed * 100) if total_closed > 0 else 0

        return {
            "total_contacts": total_contacts,
            "total_companies": total_companies,
            "total_deals": total_deals,
            "active_deals": active_deals,
            "open_deals": active_deals,
            "pipeline_value": float(pipeline_value_result["total"]),
            "won_revenue": float(won_value_result["total"]),
            "win_rate": win_rate,
            "open_tasks": open_tasks,
            "pending_tasks": open_tasks,
            "overdue_tasks": overdue_tasks,
        }

    async def _get_pipeline_summary(self) -> list:
        """Pipeline by stage — ORM annotate + group_by + values."""
        # Define stage ordering via Case expression for ORDER BY
        stage_order = Case(
            When(stage="discovery", then=Value(1)),
            When(stage="qualification", then=Value(2)),
            When(stage="proposal", then=Value(3)),
            When(stage="negotiation", then=Value(4)),
            When(stage="closed_won", then=Value(5)),
            When(stage="closed_lost", then=Value(6)),
            default=Value(99),
        )

        rows = await (
            Deal.query()
            .annotate(
                count=Count("id"),
                total_value=Coalesce(Sum("value"), Value(0)),
                stage_order=stage_order,
            )
            .group_by("stage")
            .order("stage_order")
            .values("stage", "count", "total_value")
        )
        return [{"stage": r["stage"], "count": r["count"], "value": float(r["total_value"])} for r in rows]

    async def _get_recent_activities(self) -> list:
        """Last 10 activities enriched with user names via ORM."""
        activities = await Activity.objects.order("-created_at").limit(10).all()
        result = []
        for act in activities:
            d = act.to_dict()
            # Enrich with user name via ORM
            if d.get("user_id"):
                user = await User.get(pk=d["user_id"])
                if user:
                    d["first_name"] = user.first_name
                    d["last_name"] = user.last_name
            result.append(d)
        return result

    async def _get_tasks_overview(self) -> Dict[str, Any]:
        """Task counts by status and overdue count via ORM."""
        by_status_rows = await (
            Task.query()
            .annotate(cnt=Count("id"))
            .group_by("status")
            .values("status", "cnt")
        )
        by_status = {r["status"]: r["cnt"] for r in by_status_rows}

        overdue = await (
            Task.query()
            .where("due_date < datetime('now')")
            .exclude(status__in=["completed", "cancelled"])
            .count()
        )

        return {
            "by_status": by_status,
            "overdue": overdue,
        }

    async def _get_revenue_by_stage(self) -> list:
        """Revenue grouped by deal stage via ORM."""
        rows = await (
            Deal.query()
            .annotate(revenue=Coalesce(Sum("value"), Value(0)))
            .group_by("stage")
            .values("stage", "revenue")
        )
        return [{"stage": r["stage"], "revenue": float(r["revenue"])} for r in rows]

    async def _get_contacts_by_status(self) -> list:
        """Contact distribution by status via ORM."""
        rows = await (
            Contact.query()
            .annotate(count=Count("id"))
            .group_by("status")
            .values("status", "count")
        )
        return [{"status": r["status"], "count": r["count"]} for r in rows]

    async def _get_top_deals(self) -> list:
        """Top 5 deals by value enriched with contact/company names via ORM."""
        deals = await (
            Deal.objects.exclude(stage__in=["closed_won", "closed_lost"])
            .order("-value")
            .limit(5)
            .all()
        )

        result = []
        for deal in deals:
            d = deal.to_dict()
            # Enrich with contact name
            if d.get("contact_id"):
                contact = await Contact.get(pk=d["contact_id"])
                d["contact_name"] = contact.full_name if contact else None
            else:
                d["contact_name"] = None
            # Enrich with company name
            if d.get("company_id"):
                company = await Company.get(pk=d["company_id"])
                d["company_name"] = company.name if company else None
            else:
                d["company_name"] = None
            result.append(d)
        return result

    async def _get_team_performance(self) -> list:
        """Sales rep performance — pure ORM with per-user aggregation."""
        # Get active sales users via ORM
        users = await (
            User.objects.filter(is_active=True)
            .filter(role__in=["rep", "manager"])
            .all()
        )

        result = []
        for user in users:
            uid = user.pk

            # Per-user deal aggregates via ORM
            deal_count = await Deal.objects.filter(owner_id=uid).count()

            won_rev_result = await (
                Deal.objects.filter(owner_id=uid, stage="closed_won")
                .aggregate(total=Coalesce(Sum("value"), Value(0)))
            )

            pipeline_val_result = await (
                Deal.objects.filter(owner_id=uid)
                .exclude(stage__in=["closed_won", "closed_lost"])
                .aggregate(total=Coalesce(Sum("value"), Value(0)))
            )

            contact_count = await Contact.objects.filter(owner_id=uid).count()

            result.append({
                "id": uid,
                "name": f"{user.first_name} {user.last_name}",
                "role": user.role,
                "deals": deal_count,
                "won_revenue": float(won_rev_result["total"]),
                "pipeline_value": float(pipeline_val_result["total"]),
                "contacts": contact_count,
            })

        # Sort by won_revenue descending
        result.sort(key=lambda x: x["won_revenue"], reverse=True)
        return result
