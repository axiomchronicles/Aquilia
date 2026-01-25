"""
Mode module services (business logic).

Services contain the core business logic and are auto-wired
via dependency injection.
"""

from typing import Optional, List
from aquilia.di import service


@service(scope="app")
class ModeService:
    """
    Service for mode business logic.

    This service is automatically registered with the DI container
    and can be injected into controllers.
    """

    def __init__(self):
        # TODO: Inject dependencies (e.g., repositories, external services)
        self._storage: List[dict] = []
        self._next_id = 1

    async def get_all(self) -> List[dict]:
        """Get all items."""
        return self._storage

    async def get_by_id(self, item_id: int) -> Optional[dict]:
        """Get item by ID."""
        for item in self._storage:
            if item["id"] == item_id:
                return item
        return None

    async def create(self, data: dict) -> dict:
        """Create new item."""
        item = {
            "id": self._next_id,
            **data
        }
        self._storage.append(item)
        self._next_id += 1
        return item

    async def update(self, item_id: int, data: dict) -> Optional[dict]:
        """Update existing item."""
        item = await self.get_by_id(item_id)
        if item:
            item.update(data)
        return item

    async def delete(self, item_id: int) -> bool:
        """Delete item."""
        for i, item in enumerate(self._storage):
            if item["id"] == item_id:
                self._storage.pop(i)
                return True
        return False