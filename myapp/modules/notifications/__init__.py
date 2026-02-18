"""
Notifications Module — Real-time notifications and chat.

Components:
- Services: NotificationService
- Controllers: NotificationController (REST)
- Sockets: NotificationSocket, ChatSocket, OrderTrackingSocket (WebSocket)
- Faults: Notification-specific error handling
"""

from .services import NotificationService
from .controllers import NotificationController
from .sockets import NotificationSocket, ChatSocket, OrderTrackingSocket
from .faults import (
    NotificationDeliveryFault,
    WebSocketConnectionFault,
    ChannelPermissionFault,
)

__all__ = [
    "NotificationService",
    "NotificationController",
    "NotificationSocket", "ChatSocket", "OrderTrackingSocket",
    "NotificationDeliveryFault", "WebSocketConnectionFault",
    "ChannelPermissionFault",
]
