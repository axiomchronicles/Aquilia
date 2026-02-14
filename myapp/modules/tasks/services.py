"""
Tasks Module - Services

Showcases:
- Complex business logic with validation
- Task lifecycle management (states: pending → in_progress → completed/cancelled)
- Assignee management with quota enforcement
- Statistics and filtering
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from aquilia.di import service
from .faults import (
    TaskNotFoundFault,
    TaskAlreadyCompleteFault,
    TaskAssignmentFault,
    TaskValidationFault,
    TaskQuotaExceededFault,
)


VALID_PRIORITIES = ("low", "medium", "high", "critical")
VALID_STATUSES = ("pending", "in_progress", "completed", "cancelled")
MAX_TASKS_PER_USER = 50


@service(scope="app")
class TaskService:
    """
    Task management service.

    Demonstrates structured fault handling in business logic:
    - Validation → TaskValidationFault
    - Not found → TaskNotFoundFault
    - State violations → TaskAlreadyCompleteFault
    - Assignment failures → TaskAssignmentFault
    - Quota enforcement → TaskQuotaExceededFault
    """

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._user_task_count: Dict[str, int] = {}

    async def create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task with validation."""
        # Validate
        errors = self._validate(data)
        if errors:
            raise TaskValidationFault(errors)

        # Check quota for assignee
        assignee = data.get("assignee")
        if assignee:
            count = self._user_task_count.get(assignee, 0)
            if count >= MAX_TASKS_PER_USER:
                raise TaskQuotaExceededFault(assignee, count, MAX_TASKS_PER_USER)

        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "title": data["title"],
            "description": data.get("description", ""),
            "priority": data.get("priority", "medium"),
            "status": "pending",
            "assignee": assignee,
            "tags": data.get("tags", []),
            "due_date": data.get("due_date"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }
        self._tasks[task_id] = task

        if assignee:
            self._user_task_count[assignee] = self._user_task_count.get(assignee, 0) + 1

        return task

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task by ID or raise fault."""
        task = self._tasks.get(task_id)
        if not task:
            raise TaskNotFoundFault(task_id)
        return task

    async def list_tasks(
        self,
        status: str = None,
        priority: str = None,
        assignee: str = None,
        tag: str = None,
    ) -> List[Dict[str, Any]]:
        """List tasks with filtering."""
        results = list(self._tasks.values())

        if status:
            results = [t for t in results if t["status"] == status]
        if priority:
            results = [t for t in results if t["priority"] == priority]
        if assignee:
            results = [t for t in results if t.get("assignee") == assignee]
        if tag:
            results = [t for t in results if tag in t.get("tags", [])]

        # Sort by priority (critical > high > medium > low), then by creation
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        results.sort(key=lambda t: (
            priority_order.get(t["priority"], 99),
            t["created_at"],
        ))

        return results

    async def update_task(self, task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update task, respecting state constraints."""
        task = self._tasks.get(task_id)
        if not task:
            raise TaskNotFoundFault(task_id)

        if task["status"] in ("completed", "cancelled"):
            raise TaskAlreadyCompleteFault(task_id)

        # Only allow updating safe fields
        allowed = {"title", "description", "priority", "tags", "due_date"}
        safe_data = {k: v for k, v in data.items() if k in allowed}
        task.update(safe_data)
        task["updated_at"] = datetime.utcnow().isoformat()

        return task

    async def assign_task(self, task_id: str, assignee: str) -> Dict[str, Any]:
        """Assign task to a user with quota check."""
        task = self._tasks.get(task_id)
        if not task:
            raise TaskNotFoundFault(task_id)

        if task["status"] in ("completed", "cancelled"):
            raise TaskAlreadyCompleteFault(task_id)

        # Check quota
        count = self._user_task_count.get(assignee, 0)
        if count >= MAX_TASKS_PER_USER:
            raise TaskAssignmentFault(task_id, assignee, "User at task capacity")

        # Remove from old assignee count
        old_assignee = task.get("assignee")
        if old_assignee and old_assignee in self._user_task_count:
            self._user_task_count[old_assignee] = max(0, self._user_task_count[old_assignee] - 1)

        # Assign
        task["assignee"] = assignee
        task["updated_at"] = datetime.utcnow().isoformat()
        self._user_task_count[assignee] = count + 1

        return task

    async def transition_status(self, task_id: str, new_status: str) -> Dict[str, Any]:
        """
        Transition task status.

        Valid transitions:
        - pending → in_progress, cancelled
        - in_progress → completed, cancelled
        - completed → (none)
        - cancelled → pending (reopen)
        """
        task = self._tasks.get(task_id)
        if not task:
            raise TaskNotFoundFault(task_id)

        current = task["status"]
        valid_transitions = {
            "pending": {"in_progress", "cancelled"},
            "in_progress": {"completed", "cancelled"},
            "completed": set(),
            "cancelled": {"pending"},
        }

        if new_status not in valid_transitions.get(current, set()):
            raise TaskAlreadyCompleteFault(task_id)

        task["status"] = new_status
        task["updated_at"] = datetime.utcnow().isoformat()

        if new_status == "completed":
            task["completed_at"] = datetime.utcnow().isoformat()

        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        task = self._tasks.pop(task_id, None)
        if not task:
            raise TaskNotFoundFault(task_id)

        # Decrement assignee count
        assignee = task.get("assignee")
        if assignee and assignee in self._user_task_count:
            self._user_task_count[assignee] = max(0, self._user_task_count[assignee] - 1)

        return True

    async def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        tasks = list(self._tasks.values())
        by_status = {}
        by_priority = {}

        for t in tasks:
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
            by_priority[t["priority"]] = by_priority.get(t["priority"], 0) + 1

        return {
            "total": len(tasks),
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue": sum(
                1 for t in tasks
                if t.get("due_date") and t["due_date"] < datetime.utcnow().isoformat()
                and t["status"] not in ("completed", "cancelled")
            ),
        }

    def _validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate task data."""
        errors = []

        if not data.get("title", "").strip():
            errors.append("Title is required")
        elif len(data["title"]) > 200:
            errors.append("Title must be 200 characters or less")

        priority = data.get("priority", "medium")
        if priority not in VALID_PRIORITIES:
            errors.append(f"Priority must be one of: {', '.join(VALID_PRIORITIES)}")

        return errors
