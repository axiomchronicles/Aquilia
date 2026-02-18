"""
Company Service — CRUD with caching and fault handling.
Fully wired through the Aquilia ORM.
"""

from typing import Optional, Dict, Any
from aquilia.di import service
from aquilia.cache import CacheService

from aquilia.models import Count, Sum, Coalesce, Value

from modules.shared.models import Company, Contact, Deal, User, Activity
from modules.shared.faults import CompanyNotFoundFault


@service(scope="app")
class CompanyService:
    """Business logic for company management. All queries use the ORM."""

    def __init__(self, cache: CacheService = None):
        self.cache = cache

    async def list_companies(
        self,
        search: str = None,
        industry: str = None,
        size: str = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        """List companies with filtering and pagination."""
        if search:
            s = f"%{search}%"
            qs = Company.query().where(
                "(name LIKE ? OR email LIKE ? OR city LIKE ?)", s, s, s
            )
        else:
            qs = Company.query()

        if industry:
            qs = qs.filter(industry=industry)
        if size:
            qs = qs.filter(size=size)

        total = await qs.count()
        offset = (page - 1) * per_page
        companies_list = await qs.order("name").limit(per_page).offset(offset).all()

        items = []
        for c in companies_list:
            d = c.to_dict()
            # Count contacts per company via ORM
            d["contact_count"] = await Contact.objects.filter(company_id=c.pk).count()
            # Count deals per company via ORM
            d["deal_count"] = await Deal.objects.filter(company_id=c.pk).count()
            items.append(d)

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def get_company(self, company_id: int) -> Dict[str, Any]:
        """Get single company with related data."""
        cache_key = f"company:{company_id}"

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        company = await Company.get(pk=company_id)
        if not company:
            raise CompanyNotFoundFault(company_id)

        result = company.to_dict()

        # Fetch contacts via ORM
        contacts = await Contact.objects.filter(company_id=company_id).order("-created_at").all()
        result["contacts"] = [c.to_dict() for c in contacts]

        # Fetch deals via ORM
        deals = await Deal.objects.filter(company_id=company_id).order("-created_at").all()
        result["deals"] = [d.to_dict() for d in deals]

        # Owner name via ORM
        if result.get("owner_id"):
            owner = await User.get(pk=result["owner_id"])
            result["owner_name"] = owner.full_name if owner else None

        if self.cache:
            await self.cache.set(cache_key, result, ttl=120)

        return result

    async def create_company(self, data: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """Create a new company via ORM."""
        if user_id:
            data["owner_id"] = user_id
        company = await Company.create(**data)
        return company.to_dict()

    async def update_company(self, company_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a company via ORM instance save."""
        company = await Company.get(pk=company_id)
        if not company:
            raise CompanyNotFoundFault(company_id)

        changed = []
        for key, value in data.items():
            if value is not None and hasattr(company, key):
                setattr(company, key, value)
                changed.append(key)

        if changed:
            await company.save(update_fields=changed)

        if self.cache:
            await self.cache.delete(f"company:{company_id}")

        return await self.get_company(company_id)

    async def delete_company(self, company_id: int) -> bool:
        """Delete a company via ORM."""
        company = await Company.get(pk=company_id)
        if not company:
            raise CompanyNotFoundFault(company_id)

        await company.delete_instance()

        if self.cache:
            await self.cache.delete(f"company:{company_id}")

        return True

    async def get_company_stats(self) -> Dict[str, Any]:
        """Company statistics for dashboard using ORM aggregates."""
        total = await Company.objects.count()

        # GROUP BY aggregations via ORM annotate + group_by + values
        by_industry_rows = await (
            Company.query()
            .annotate(cnt=Count("id"))
            .group_by("industry")
            .values("industry", "cnt")
        )
        by_size_rows = await (
            Company.query()
            .annotate(cnt=Count("id"))
            .group_by("size")
            .values("size", "cnt")
        )

        # Total revenue via ORM aggregate
        total_revenue_result = await Company.objects.aggregate(
            total=Coalesce(Sum("annual_revenue"), Value(0))
        )

        return {
            "total": total,
            "by_industry": {r["industry"]: r["cnt"] for r in by_industry_rows},
            "by_size": {r["size"]: r["cnt"] for r in by_size_rows},
            "total_revenue": float(total_revenue_result["total"]),
        }
