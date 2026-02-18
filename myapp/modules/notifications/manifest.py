"""
Notifications Module Manifest — Real-time notifications, chat & tracking.

Defines complete module configuration:
- Services: NotificationService
- Controllers: NotificationController (REST)
- Socket Controllers: NotificationSocket, ChatSocket, OrderTrackingSocket (WS)
- Fault domain: NOTIFICATIONS
"""

from aquilia import AppManifest
from aquilia.manifest import (
    FaultHandlingConfig,
    MiddlewareConfig,
    FeatureConfig,
)


manifest = AppManifest(
    # ── Identity ──────────────────────────────────────────────────────
    name="notifications",
    version="1.0.0",
    description="Real-time notifications, chat rooms & order tracking via WebSocket",
    author="nexus-engineering@nexus-platform.com",
    tags=["notifications", "websocket", "chat", "realtime"],

    # ── Services ──────────────────────────────────────────────────────
    services=[
        "modules.notifications.services:NotificationService",
    ],

    # ── Controllers ───────────────────────────────────────────────────
    controllers=[
        "modules.notifications.controllers:NotificationController",
    ],

    # ── Socket Controllers ────────────────────────────────────────────
    socket_controllers=[
        "modules.notifications.sockets:NotificationSocket",
        "modules.notifications.sockets:ChatSocket",
        "modules.notifications.sockets:OrderTrackingSocket",
    ],

    # ── Middleware ─────────────────────────────────────────────────────
    middleware=[],

    # ── Routing ───────────────────────────────────────────────────────
    route_prefix="/notifications",
    base_path="modules.notifications",

    # ── Faults ────────────────────────────────────────────────────────
    faults=FaultHandlingConfig(
        default_domain="NOTIFICATIONS",
        strategy="propagate",
        handlers=[],
    ),

    # ── Sessions ──────────────────────────────────────────────────────
    sessions=[],

    # ── Features ──────────────────────────────────────────────────────
    features=[
        FeatureConfig(name="push_notifications", enabled=False),
        FeatureConfig(name="email_notifications", enabled=True),
        FeatureConfig(name="chat_rooms", enabled=True),
        FeatureConfig(name="order_tracking_ws", enabled=True),
    ],

    # ── Dependencies ──────────────────────────────────────────────────
    depends_on=["users"],
)


__all__ = ["manifest"]
