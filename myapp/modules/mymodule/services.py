"""
Mymodule module services (business logic).

Services contain the core business logic and are auto-wired
via dependency injection.
"""

from typing import Optional, List
from aquilia.di import service
from aquilia.sessions import Session


@service(scope="app")
class MymoduleService:
    """
    Service for mymodule business logic.

    This service is automatically registered with the DI container
    and can be injected into controllers. Provides session-aware operations.
    """

    def __init__(self):
        # TODO: Inject dependencies (e.g., repositories, external services)
        self._storage: List[dict] = []
        self._user_data: dict = {}  # user_id -> user items
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

    # Session-aware methods
    async def get_user_items(self, session: Optional[Session]) -> List[dict]:
        """Get items for the current user session."""
        if not session:
            return []
            
        # Access session data safely
        data = getattr(session, "data", {})
        user_id = data.get("user_id")
        
        if not user_id:
            return []
        return self._user_data.get(user_id, [])

    async def create_user_item(self, session: Optional[Session], data: dict) -> dict:
        """Create item for the current user."""
        if not session:
            # Fallback for sessionless creation
            user_id = "anonymous"
        else:
            # Access session data safely
            sess_data = getattr(session, "data", {})
            user_id = sess_data.get("user_id")
            
            if not user_id:
                # Auto-assign user ID based on session
                user_id = f"user_{session.id}"
                session.data["user_id"] = user_id
        
        if user_id not in self._user_data:
            self._user_data[user_id] = []
        
        item = {
            "id": self._next_id,
            "user_id": user_id,
            "session_id": str(session.id) if session else "no-session",
            **data
        }
        self._user_data[user_id].append(item)
        self._next_id += 1
        return item

    async def get_session_info(self, session: Optional[Session]) -> dict:
        """Get session information and user data."""
        if not session:
            return {
                "session_id": "no-session",
                "user_id": None,
                "session_data": {},
                "user_items_count": 0,
                "is_authenticated": False,
                "principal_id": None,
            }

        user_id = session.data.get("user_id")
        user_items = await self.get_user_items(session)
        
        return {
            "session_id": str(session.id),
            "user_id": user_id,
            "session_data": dict(session.data),
            "user_items_count": len(user_items),
            "created_at": session.created_at.isoformat(),
            "last_accessed_at": session.last_accessed_at.isoformat(),
            "is_authenticated": session.principal is not None,
            "principal_id": session.principal.id if session.principal else None,
        }