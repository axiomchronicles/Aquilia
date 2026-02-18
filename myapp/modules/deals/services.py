"""
Deal Service — Pipeline management, stage transitions, stats.
Fully wired through the Aquilia ORM.
"""

from typing import Dict, Any
from aquilia.di import service
from aquilia.cache import CacheService

from aquilia.models import Count, Sum, Coalesce, Value, F

from modules.shared.models import Deal, Contact, Company, User, Task, Note, Activity
from modules.shared.faults import DealNotFoundFault, InvalidStageTransitionFault


# Valid stage transitions
STAGE_ORDER = ["discovery", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]
VALID_TRANSITIONS = {
    "discovery": ["qualification", "closed_lost"],
    "qualification": ["proposal", "discovery", "closed_lost"],
    "proposal": ["negotiation", "qualification", "closed_lost"],
    "negotiation": ["closed_won", "closed_lost", "proposal"],
    "closed_won": [],
    "closed_lost": ["discovery"],
}

STAGE_PROBABILITIES = {
    "discovery": 10,
    "qualification": 25,
    "proposal": 50,
    "negotiation": 75,
    "closed_won": 100,
    "closed_lost": 0,
}


@service(scope="app")
class DealService:
    """Business logic for deals/pipeline management. All queries use the ORM."""

    def __init__(self, cache: CacheService = None):
        self.cache = cache

    async def list_deals(
        self,
        search: str = None,
        stage: str = None,
        priority: str = None,
        owner_id: int = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        """List deals with filtering and pagination."""
        if search:
            s = f"%{search}%"
            qs = Deal.query().where(
                "(title LIKE ? OR description LIKE ?)", s, s
            )
        else:
            qs = Deal.query()

        if stage:
            qs = qs.filter(stage=stage)
        if priority:
            qs = qs.filter(priority=priority)
        if owner_id:
            qs = qs.filter(owner_id=owner_id)

        total = await qs.count()
        offset = (page - 1) * per_page
        deals_list = await qs.order("-created_at").limit(per_page).offset(offset).all()

        items = []
        for deal in deals_list:
            d = deal.to_dict()
            # Enrich with contact name via ORM
            if d.get("contact_id"):
                contact = await Contact.get(pk=d["contact_id"])
                d["contact_name"] = contact.full_name if contact else None
            # Enrich with company name via ORM
            if d.get("company_id"):
                company = await Company.get(pk=d["company_id"])
                d["company_name"] = company.name if company else None
            items.append(d)

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def get_deal(self, deal_id: int) -> Dict[str, Any]:
        """Get single deal with enrichment via ORM."""
        deal = await Deal.get(pk=deal_id)
        if not deal:
            raise DealNotFoundFault(deal_id)

        result = deal.to_dict()

        # Contact via ORM
        if result.get("contact_id"):
            contact = await Contact.get(pk=result["contact_id"])
            result["contact"] = contact.to_dict() if contact else None

        # Company via ORM
        if result.get("company_id"):
            company = await Company.get(pk=result["company_id"])
            result["company"] = company.to_dict() if company else None

        # Owner via ORM
        if result.get("owner_id"):
            owner = await User.get(pk=result["owner_id"])
            result["owner_name"] = owner.full_name if owner else None

        # Tasks via ORM
        tasks = await Task.objects.filter(deal_id=deal_id).order("due_date").all()
        result["tasks"] = [t.to_dict() for t in tasks]

        # Notes via ORM
        notes = await Note.objects.filter(
            entity_type="deal", entity_id=deal_id
        ).order("-created_at").all()
        result["notes"] = [n.to_dict() for n in notes]

        return result

    async def create_deal(self, data: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """Create a new deal via ORM."""
        if user_id:
            data["owner_id"] = user_id
        # Auto-set probability based on stage
        stage = data.get("stage", "discovery")
        if "probability" not in data:
            data["probability"] = STAGE_PROBABILITIES.get(stage, 10)
        deal = await Deal.create(**data)
        return deal.to_dict()

    async def update_deal(self, deal_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a deal via ORM instance save."""
        deal = await Deal.get(pk=deal_id)
        if not deal:
            raise DealNotFoundFault(deal_id)

        # Validate stage transition
        if "stage" in data and data["stage"] != deal.stage:
            valid = VALID_TRANSITIONS.get(deal.stage, [])
            if data["stage"] not in valid:
                raise InvalidStageTransitionFault(deal.stage, data["stage"])
            # Auto-update probability
            data["probability"] = STAGE_PROBABILITIES.get(data["stage"], deal.probability)
            # Set close date if closing
            if data["stage"] in ("closed_won", "closed_lost"):
                from datetime import datetime, timezone
                data["actual_close_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        changed = []
        for key, value in data.items():
            if value is not None and hasattr(deal, key):
                setattr(deal, key, value)
                changed.append(key)

        if changed:
            await deal.save(update_fields=changed)

        if self.cache:
            await self.cache.delete(f"deal:{deal_id}")

        return await self.get_deal(deal_id)

    async def delete_deal(self, deal_id: int) -> bool:
        """Delete a deal via ORM."""
        deal = await Deal.get(pk=deal_id)
        if not deal:
            raise DealNotFoundFault(deal_id)
        await deal.delete_instance()
        return True

    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Pipeline statistics for dashboard using ORM aggregates."""
        total = await Deal.objects.count()

        # Total pipeline value (excluding closed_lost) via ORM aggregate
        total_value_result = await (
            Deal.objects.exclude(stage="closed_lost")
            .aggregate(total=Coalesce(Sum("value"), Value(0)))
        )

        # Won revenue via ORM aggregate
        won_value_result = await (
            Deal.objects.filter(stage="closed_won")
            .aggregate(total=Coalesce(Sum("value"), Value(0)))
        )

        # By stage: COUNT + SUM via ORM annotate + group_by + values
        by_stage_rows = await (
            Deal.query()
            .annotate(cnt=Count("id"), total_value=Coalesce(Sum("value"), Value(0)))
            .group_by("stage")
            .values("stage", "cnt", "total_value")
        )

        # By priority: COUNT via ORM annotate + group_by + values
        by_priority_rows = await (
            Deal.query()
            .annotate(cnt=Count("id"))
            .group_by("priority")
            .values("priority", "cnt")
        )

        # Weighted pipeline via ORM aggregate with expression
        weighted_result = await (
            Deal.objects.exclude(stage__in=["closed_won", "closed_lost"])
            .aggregate(
                weighted=Coalesce(Sum(F("value") * F("probability") / Value(100.0)), Value(0))
            )
        )

        return {
            "total": total,
            "total_pipeline_value": float(total_value_result["total"]),
            "won_value": float(won_value_result["total"]),
            "weighted_pipeline": float(weighted_result["weighted"]),
            "by_stage": {r["stage"]: {"count": r["cnt"], "value": float(r["total_value"])} for r in by_stage_rows},
            "by_priority": {r["priority"]: r["cnt"] for r in by_priority_rows},
        }

    async def get_pipeline_board(self) -> Dict[str, list]:
        """Get deals grouped by stage for Kanban board via ORM."""
        result = {}
        for stage in STAGE_ORDER:
            deals = await Deal.objects.filter(stage=stage).order("-value").all()
            items = []
            for deal in deals:
                d = deal.to_dict()
                if d.get("contact_id"):
                    contact = await Contact.get(pk=d["contact_id"])
                    d["contact_name"] = contact.full_name if contact else None
                items.append(d)
            result[stage] = items
        return result
