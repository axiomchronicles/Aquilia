"""
Chat Module - HTTP Controllers

Showcases:
- REST API alongside WebSocket controllers
- Chat room management endpoints
- Message history retrieval
- Online presence endpoints
- Template rendering with TemplateEngine
"""

from aquilia import Controller, GET, POST, DELETE, RequestCtx, Response
from aquilia.templates import TemplateEngine
from .services import ChatRoomService, MessageService, PresenceService


class ChatController(Controller):
    """
    Chat REST API controller with template rendering.

    Provides HTTP endpoints for:
    - Web UI (template-rendered)
    - Room management (CRUD)
    - Message history
    - Online user presence

    Works alongside ChatSocket for real-time communication.
    """

    prefix = "/"
    tags = ["chat", "rooms"]

    def __init__(
        self,
        rooms: ChatRoomService = None,
        messages: MessageService = None,
        presence: PresenceService = None,
        templates: TemplateEngine = None,
    ):
        self.rooms = rooms or ChatRoomService()
        self.messages = messages or MessageService()
        self.presence = presence or PresenceService()
        self.templates = templates

    # ── Web UI ───────────────────────────────────────────────────────────

    @GET("/")
    async def chat_index(self, ctx: RequestCtx):
        """
        Render the main chat interface.

        GET /chat
        """
        if self.templates:
            return await self.templates.render_to_response(
                "chat_index.html",
                {},
                request_ctx=ctx
            )
        return Response.html(
            "<h1>Chat</h1><p>Template engine not available. Enable templates in config.</p>"
        )

    @GET("/room/«room_id:str»")
    async def room_details(self, ctx: RequestCtx, room_id: str):
        """
        Render room details page.

        GET /chat/room/<room_id>
        """
        room = await self.rooms.get_room(room_id)
        if not room:
            return Response.html("<h1>404</h1><p>Room not found</p>", status=404)

        messages = await self.messages.get_history(room_id, limit=20)

        if self.templates:
            return await self.templates.render_to_response(
                "chat_room.html",
                {
                    "room": room,
                    "messages": messages,
                },
                request_ctx=ctx
            )
        return Response.json({"room": room, "messages": messages})

    # ── Rooms ────────────────────────────────────────────────────────────

    @GET("/rooms")
    async def list_rooms(self, ctx: RequestCtx):
        """
        List all chat rooms.

        GET /chat/rooms
        """
        rooms = await self.rooms.list_rooms()
        return Response.json({
            "rooms": rooms,
            "total": len(rooms),
        })

    @POST("/rooms")
    async def create_room(self, ctx: RequestCtx):
        """
        Create a new chat room.

        POST /chat/rooms
        Body: {"name": "Tech Talk", "description": "...", "is_public": true}
        """
        data = await ctx.json()
        name = data.get("name", "")
        if not name:
            return Response.json({"error": "Room name required"}, status=400)

        room = await self.rooms.create_room(
            name=name,
            description=data.get("description", ""),
            is_public=data.get("is_public", True),
        )
        return Response.json(room, status=201)

    @DELETE("/rooms/«room_id:str»")
    async def delete_room(self, ctx: RequestCtx, room_id: str):
        """
        Delete a chat room.

        DELETE /chat/rooms/<room_id>
        """
        deleted = await self.rooms.delete_room(room_id)
        if not deleted:
            return Response.json({"error": "Room not found"}, status=404)
        return Response.json({"deleted": True, "room_id": room_id})

    # ── Messages ─────────────────────────────────────────────────────────

    @GET("/rooms/«room_id:str»/messages")
    async def get_messages(self, ctx: RequestCtx, room_id: str):
        """
        Get message history for a room.

        GET /chat/rooms/<room_id>/messages?limit=50
        """
        limit = int(ctx.query_params.get("limit", "50"))
        messages = await self.messages.get_history(room_id, limit=limit)
        return Response.json({
            "room_id": room_id,
            "messages": messages,
            "total": len(messages),
        })

    # ── Presence ─────────────────────────────────────────────────────────

    @GET("/online")
    async def get_online_users(self, ctx: RequestCtx):
        """
        Get list of online users.

        GET /chat/online
        """
        users = await self.presence.get_online_users()
        count = await self.presence.get_online_count()
        return Response.json({
            "online_users": users,
            "count": count,
        })

    @GET("/stats")
    async def get_stats(self, ctx: RequestCtx):
        """
        Get chat statistics.

        GET /chat/stats
        """
        msg_stats = await self.messages.get_stats()
        online = await self.presence.get_online_count()
        rooms = await self.rooms.list_rooms()

        return Response.json({
            "rooms": len(rooms),
            "online_users": online,
            **msg_stats,
        })
