"""
Notifications Module — Services

Real-time notification delivery via cache-backed queues,
mail fallback, and WebSocket push coordination.
"""

from typing import Optional
from datetime import datetime, timezone

from aquilia.di import service, Inject
from aquilia.cache import CacheService, cached
from aquilia.mail import EmailMessage
from aquilia.mail.service import MailService

from .faults import NotificationDeliveryFault


@service(scope="app")
class NotificationService:
    """
    Notification orchestrator.

    Integrates:
    - Aquilia Cache (notification queue/storage)
    - Aquilia Mail (email fallback)
    - Aquilia WebSockets (live push via SocketController)
    """

    def __init__(
        self,
        cache: CacheService = Inject(CacheService),
        mail: MailService = Inject(MailService),
    ):
        self.cache = cache
        self.mail = mail

    async def send_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        category: str = "general",
        metadata: dict = None,
        send_email: bool = False,
        email_address: str = "",
    ) -> dict:
        """
        Create and store a notification.
        Optionally sends email via Aquilia MailService.
        """
        notification = {
            "id": f"ntf_{user_id}_{datetime.now(timezone.utc).timestamp()}",
            "user_id": user_id,
            "title": title,
            "body": body,
            "category": category,
            "metadata": metadata or {},
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # store in cache with 7-day TTL
        cache_key = f"notifications:{user_id}"
        existing = await self.cache.get(cache_key, namespace="notifications") or []
        existing.insert(0, notification)
        # keep last 100 notifications
        existing = existing[:100]
        await self.cache.set(cache_key, existing, ttl=604800, namespace="notifications")

        # email fallback
        if send_email and email_address:
            try:
                msg = EmailMessage(
                    subject=title,
                    to=[email_address],
                    body=body,
                )
                await self.mail.asend_mail(msg)
            except Exception:
                pass

        return notification

    @cached(ttl=30, namespace="notifications")
    async def get_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list:
        cache_key = f"notifications:{user_id}"
        notifications = await self.cache.get(cache_key, namespace="notifications") or []
        if unread_only:
            notifications = [n for n in notifications if not n.get("is_read")]
        return notifications[:limit]

    async def mark_read(self, user_id: int, notification_id: str) -> None:
        cache_key = f"notifications:{user_id}"
        notifications = await self.cache.get(cache_key, namespace="notifications") or []
        for ntf in notifications:
            if ntf["id"] == notification_id:
                ntf["is_read"] = True
                break
        await self.cache.set(cache_key, notifications, ttl=604800, namespace="notifications")

    async def mark_all_read(self, user_id: int) -> int:
        cache_key = f"notifications:{user_id}"
        notifications = await self.cache.get(cache_key, namespace="notifications") or []
        count = 0
        for ntf in notifications:
            if not ntf["is_read"]:
                ntf["is_read"] = True
                count += 1
        await self.cache.set(cache_key, notifications, ttl=604800, namespace="notifications")
        return count

    async def get_unread_count(self, user_id: int) -> int:
        cache_key = f"notifications:{user_id}"
        notifications = await self.cache.get(cache_key, namespace="notifications") or []
        return sum(1 for n in notifications if not n.get("is_read"))

    async def broadcast_system_notification(
        self, title: str, body: str, user_ids: list
    ) -> int:
        """Broadcast to multiple users."""
        sent = 0
        for uid in user_ids:
            try:
                await self.send_notification(uid, title, body, category="system")
                sent += 1
            except Exception:
                continue
        return sent
