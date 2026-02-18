"""
Contact Service — CRUD with caching, DI, and fault handling.
Fully wired through the Aquilia ORM.
"""

from typing import Optional, Dict, Any, List
from aquilia.di import service
from aquilia.cache import CacheService

from aquilia.models import Count

from modules.shared.models import Contact, Company, User, Activity, Note
from modules.shared.faults import ContactNotFoundFault, DuplicateContactFault


@service(scope="app")
class ContactService:
    """Business logic for contact management. All queries use the ORM."""

    def __init__(self, cache: CacheService = None):
        self.cache = cache

    async def list_contacts(
        self,
        search: str = None,
        status: str = None,
        source: str = None,
        owner_id: int = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        """List contacts with filtering, search, and pagination."""
        qs = Contact.objects

        if search:
            # Multi-field search via ORM raw where clause
            s = f"%{search}%"
            qs = Contact.query().where(
                "(first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR job_title LIKE ?)",
                s, s, s, s,
            )
        else:
            qs = Contact.query()

        if status:
            qs = qs.filter(status=status)
        if source:
            qs = qs.filter(source=source)
        if owner_id:
            qs = qs.filter(owner_id=owner_id)

        total = await qs.count()
        offset = (page - 1) * per_page
        contacts_list = await qs.order("-created_at").limit(per_page).offset(offset).all()

        return {
            "items": [c.to_dict() for c in contacts_list],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def get_contact(self, contact_id: int) -> Dict[str, Any]:
        """Get single contact with caching."""
        cache_key = f"contact:{contact_id}"

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        contact = await Contact.get(pk=contact_id)
        if not contact:
            raise ContactNotFoundFault(contact_id)

        result = contact.to_dict()

        # Enrich: company name
        if result.get("company_id"):
            company = await Company.get(pk=result["company_id"])
            result["company_name"] = company.name if company else None

        # Enrich: owner name
        if result.get("owner_id"):
            owner = await User.get(pk=result["owner_id"])
            result["owner_name"] = owner.full_name if owner else None

        # Enrich: notes via ORM
        notes = await Note.objects.filter(
            entity_type="contact", entity_id=contact_id
        ).order("-created_at").limit(10).all()
        result["notes"] = [n.to_dict() for n in notes]

        if self.cache:
            await self.cache.set(cache_key, result, ttl=120)

        return result

    async def create_contact(self, data: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """Create a new contact."""
        # Check duplicate email via ORM
        existing = await Contact.objects.filter(email=data["email"]).exists()
        if existing:
            raise DuplicateContactFault(data["email"])

        if user_id:
            data["owner_id"] = user_id

        # ORM create — signals will auto-log activity
        contact = await Contact.create(**data)

        return contact.to_dict()

    async def update_contact(self, contact_id: int, data: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """Update an existing contact via ORM instance save."""
        contact = await Contact.get(pk=contact_id)
        if not contact:
            raise ContactNotFoundFault(contact_id)

        changed = []
        for key, value in data.items():
            if value is not None and hasattr(contact, key):
                setattr(contact, key, value)
                changed.append(key)

        if changed:
            await contact.save(update_fields=changed)

        # Invalidate cache
        if self.cache:
            await self.cache.delete(f"contact:{contact_id}")

        return await self.get_contact(contact_id)

    async def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact via ORM."""
        contact = await Contact.get(pk=contact_id)
        if not contact:
            raise ContactNotFoundFault(contact_id)

        await contact.delete_instance()

        if self.cache:
            await self.cache.delete(f"contact:{contact_id}")

        return True

    async def get_contact_stats(self) -> Dict[str, Any]:
        """Get contact statistics for dashboard using ORM aggregates."""
        total = await Contact.objects.count()

        # Group-by queries via ORM annotate + group_by + values
        by_status_rows = await (
            Contact.query()
            .annotate(cnt=Count("id"))
            .group_by("status")
            .values("status", "cnt")
        )
        by_source_rows = await (
            Contact.query()
            .annotate(cnt=Count("id"))
            .group_by("source")
            .values("source", "cnt")
        )

        recent = await Contact.objects.order("-created_at").limit(5).all()

        return {
            "total": total,
            "by_status": {r["status"]: r["cnt"] for r in by_status_rows},
            "by_source": {r["source"]: r["cnt"] for r in by_source_rows},
            "recent": [c.to_dict() for c in recent],
        }
