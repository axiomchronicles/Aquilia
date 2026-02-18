"""
Task Service — CRUD, assignment, stats.
Fully wired through the Aquilia ORM.
"""

from typing import Dict, Any
from aquilia.di import service
from aquilia.cache import CacheService

from aquilia.models import Count

from modules.shared.models import Task, User, Contact, Deal
from modules.shared.faults import TaskNotFoundFault


@service(scope="app")
class TaskService:
    """Business logic for task management. All queries use the ORM."""

    def __init__(self, cache: CacheService = None):
        self.cache = cache

    async def list_tasks(
        self,
        search: str = None,
        status: str = None,
        priority: str = None,
        assigned_to_id: int = None,
        task_type: str = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        if search:
            s = f"%{search}%"
            qs = Task.query().where(
                "(title LIKE ? OR description LIKE ?)", s, s
            )
        else:
            qs = Task.query()

        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if assigned_to_id:
            qs = qs.filter(assigned_to_id=assigned_to_id)
        if task_type:
            qs = qs.filter(task_type=task_type)

        total = await qs.count()
        offset = (page - 1) * per_page

        tasks_list = await qs.order("due_date").limit(per_page).offset(offset).all()

        items = []
        for task in tasks_list:
            t = task.to_dict()
            if t.get("assigned_to_id"):
                user = await User.get(pk=t["assigned_to_id"])
                t["assigned_to_name"] = user.full_name if user else None
            if t.get("contact_id"):
                contact = await Contact.get(pk=t["contact_id"])
                t["contact_name"] = contact.full_name if contact else None
            items.append(t)

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def get_task(self, task_id: int) -> Dict[str, Any]:
        task = await Task.get(pk=task_id)
        if not task:
            raise TaskNotFoundFault(task_id)

        result = task.to_dict()

        # Enrich via ORM
        if result.get("assigned_to_id"):
            user = await User.get(pk=result["assigned_to_id"])
            if user:
                result["assigned_to"] = {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                }

        if result.get("contact_id"):
            contact = await Contact.get(pk=result["contact_id"])
            if contact:
                result["contact"] = {
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "email": contact.email,
                }

        if result.get("deal_id"):
            deal = await Deal.get(pk=result["deal_id"])
            if deal:
                result["deal"] = {
                    "title": deal.title,
                    "stage": deal.stage,
                    "value": deal.value,
                }

        return result

    async def create_task(self, data: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        if user_id:
            data["created_by_id"] = user_id
        task = await Task.create(**data)
        return task.to_dict()

    async def update_task(self, task_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        task = await Task.get(pk=task_id)
        if not task:
            raise TaskNotFoundFault(task_id)

        # If marking completed, set completed_at
        if data.get("status") == "completed":
            from datetime import datetime, timezone
            data["completed_at"] = datetime.now(timezone.utc).isoformat()

        changed = []
        for key, value in data.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
                changed.append(key)

        if changed:
            await task.save(update_fields=changed)

        return await self.get_task(task_id)

    async def delete_task(self, task_id: int) -> bool:
        task = await Task.get(pk=task_id)
        if not task:
            raise TaskNotFoundFault(task_id)
        await task.delete_instance()
        return True

    async def get_task_stats(self) -> Dict[str, Any]:
        """Task statistics using ORM aggregates."""
        total = await Task.objects.count()

        # GROUP BY aggregations via ORM annotate + group_by + values
        by_status_rows = await (
            Task.query()
            .annotate(cnt=Count("id"))
            .group_by("status")
            .values("status", "cnt")
        )
        by_priority_rows = await (
            Task.query()
            .annotate(cnt=Count("id"))
            .group_by("priority")
            .values("priority", "cnt")
        )
        by_type_rows = await (
            Task.query()
            .annotate(cnt=Count("id"))
            .group_by("task_type")
            .values("task_type", "cnt")
        )

        # Overdue count via ORM where + exclude + count
        overdue = await (
            Task.query()
            .where("due_date < datetime('now')")
            .exclude(status__in=["completed", "cancelled"])
            .count()
        )

        return {
            "total": total,
            "by_status": {r["status"]: r["cnt"] for r in by_status_rows},
            "by_priority": {r["priority"]: r["cnt"] for r in by_priority_rows},
            "by_type": {r["task_type"]: r["cnt"] for r in by_type_rows},
            "overdue": overdue,
        }
