"""
Chat Module - Manifest

Showcases WebSocket controller registration alongside HTTP controllers.
"""

from aquilia import AppManifest
from aquilia.manifest import FaultHandlingConfig, FeatureConfig

manifest = AppManifest(
    name="chat",
    version="0.1.0",
    description="Real-time chat with WebSockets, rooms, presence, and message history",
    author="team@aquilia.dev",
    tags=["chat", "websocket", "realtime"],

    services=[
        "modules.chat.services:ChatRoomService",
        "modules.chat.services:MessageService",
        "modules.chat.services:PresenceService",
    ],
    controllers=[
        "modules.chat.controllers:ChatController",
        "modules.chat.sockets:ChatSocket",
        "modules.chat.sockets:NotificationSocket",
    ],

    route_prefix="/chat",
    base_path="modules.chat",

    faults=FaultHandlingConfig(
        default_domain="CHAT",
        strategy="propagate",
        handlers=[],
    ),

    features=[
        FeatureConfig(name="chat_rooms", enabled=True),
        FeatureConfig(name="chat_history", enabled=True),
        FeatureConfig(name="typing_indicators", enabled=True),
        FeatureConfig(name="file_sharing", enabled=False),
    ],
)
