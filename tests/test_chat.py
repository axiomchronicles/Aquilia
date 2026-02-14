"""
Tests for the myapp/modules/chat module.

Covers:
- ChatRoomService, MessageService, PresenceService
- ChatController HTTP endpoints
- ChatSocket & NotificationSocket WebSocket controllers
- Connection convenience API (id, send_json, join_room, leave_room)
- SocketController.publish_room with exclude_connection
- on_disconnect with reason parameter
- Runtime _call_on_disconnect signature introspection
- MessageEnvelope dual-format parsing (payload vs data)
- AckEvent dispatch (handler ack vs client ack)
- send_envelope metrics tracking
- AquilaSockets initialize/shutdown lifecycle
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Framework imports ────────────────────────────────────────────────────────

from aquilia.sockets import (
    SocketController,
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    AckEvent,
    Connection,
    ConnectionScope,
    ConnectionState,
    InMemoryAdapter,
    MessageEnvelope,
    MessageType,
    JSONCodec,
)
from aquilia.sockets.runtime import AquilaSockets, SocketRouter, RouteMetadata
from aquilia.response import Response

# ── App imports ──────────────────────────────────────────────────────────────

from myapp.modules.chat.services import (
    ChatRoomService,
    MessageService,
    PresenceService,
)
from myapp.modules.chat.sockets import ChatSocket, NotificationSocket


# ═════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═════════════════════════════════════════════════════════════════════════════


def _make_connection(
    connection_id: str = None,
    namespace: str = "/chat",
    adapter: InMemoryAdapter = None,
) -> Connection:
    """Build a lightweight Connection for unit testing."""
    connection_id = connection_id or str(uuid.uuid4())
    adapter = adapter or InMemoryAdapter()
    scope = ConnectionScope(
        namespace=namespace,
        path=namespace,
        path_params={},
        query_params={},
        headers={},
    )
    # Keep sent bytes for assertions
    sent_data: List[bytes] = []

    async def send_func(data: bytes):
        sent_data.append(data)

    conn = Connection(
        connection_id=connection_id,
        namespace=namespace,
        scope=scope,
        container=MagicMock(),
        adapter=adapter,
        send_func=send_func,
    )
    conn._sent_data = sent_data  # stash for test inspection
    conn.mark_connected()
    return conn


# ═════════════════════════════════════════════════════════════════════════════
#  Service Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestChatRoomService:

    @pytest.fixture
    def svc(self):
        return ChatRoomService()

    @pytest.mark.asyncio
    async def test_default_rooms(self, svc):
        rooms = await svc.list_rooms()
        names = {r["id"] for r in rooms}
        assert "general" in names
        assert "random" in names

    @pytest.mark.asyncio
    async def test_get_room(self, svc):
        room = await svc.get_room("general")
        assert room is not None
        assert room["name"] == "General"

    @pytest.mark.asyncio
    async def test_get_room_missing(self, svc):
        assert await svc.get_room("nonexistent") is None

    @pytest.mark.asyncio
    async def test_create_room(self, svc):
        room = await svc.create_room("Tech Talk", description="Discussing tech")
        assert room["id"] == "tech-talk"
        assert room["name"] == "Tech Talk"
        assert room["is_public"] is True
        # Should be findable now
        assert await svc.get_room("tech-talk") is not None

    @pytest.mark.asyncio
    async def test_delete_room(self, svc):
        await svc.create_room("temp")
        assert await svc.delete_room("temp") is True
        assert await svc.get_room("temp") is None

    @pytest.mark.asyncio
    async def test_delete_room_missing(self, svc):
        assert await svc.delete_room("nope") is False


class TestMessageService:

    @pytest.fixture
    def svc(self):
        return MessageService()

    @pytest.mark.asyncio
    async def test_seed_messages(self, svc):
        history = await svc.get_history("general")
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_add_message(self, svc):
        msg = await svc.add_message("general", "alice", "hello")
        assert msg["sender"] == "alice"
        assert msg["text"] == "hello"
        assert msg["room_id"] == "general"

    @pytest.mark.asyncio
    async def test_history_limit(self, svc):
        for i in range(10):
            await svc.add_message("room_x", "bot", f"msg {i}")
        history = await svc.get_history("room_x", limit=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_stats(self, svc):
        stats = await svc.get_stats()
        assert "total_messages" in stats
        assert stats["total_messages"] >= 0


class TestPresenceService:

    @pytest.fixture
    def svc(self):
        return PresenceService()

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, svc):
        await svc.user_connected("c1", "alice")
        assert await svc.get_online_count() == 1
        users = await svc.get_online_users()
        assert "alice" in users

        uname = await svc.user_disconnected("c1")
        assert uname == "alice"
        assert await svc.get_online_count() == 0

    @pytest.mark.asyncio
    async def test_join_leave_room(self, svc):
        await svc.user_connected("c1", "bob")
        await svc.join_room("c1", "general")
        members = await svc.get_room_members("general")
        assert "bob" in members

        await svc.leave_room("c1", "general")
        members = await svc.get_room_members("general")
        assert "bob" not in members

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_rooms(self, svc):
        await svc.user_connected("c1", "charlie")
        await svc.join_room("c1", "general")
        await svc.user_disconnected("c1")
        members = await svc.get_room_members("general")
        assert len(members) == 0


# ═════════════════════════════════════════════════════════════════════════════
#  Connection convenience API tests
# ═════════════════════════════════════════════════════════════════════════════


class TestConnectionConvenienceAPI:
    """Verify the id, send_json, join_room, leave_room additions."""

    def test_id_property(self):
        conn = _make_connection(connection_id="abc-123")
        assert conn.id == "abc-123"
        assert conn.id == conn.connection_id

    @pytest.mark.asyncio
    async def test_send_json(self):
        conn = _make_connection()
        await conn.send_json({"hello": "world"})
        assert len(conn._sent_data) == 1
        parsed = json.loads(conn._sent_data[0])
        assert parsed == {"hello": "world"}

    @pytest.mark.asyncio
    async def test_join_room_alias(self):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        joined = await conn.join_room("test-room")
        assert joined is True
        assert "test-room" in conn.rooms

    @pytest.mark.asyncio
    async def test_leave_room_alias(self):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        await conn.join_room("test-room")
        left = await conn.leave_room("test-room")
        assert left is True
        assert "test-room" not in conn.rooms


# ═════════════════════════════════════════════════════════════════════════════
#  ChatSocket lifecycle tests
# ═════════════════════════════════════════════════════════════════════════════


class TestChatSocketOnConnect:
    """Test ChatSocket.on_connect handler."""

    @pytest.fixture
    def socket(self):
        s = ChatSocket()
        s.adapter = InMemoryAdapter()
        return s

    @pytest.mark.asyncio
    async def test_on_connect_sets_username(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        await socket.on_connect(conn)

        assert "username" in conn.state
        assert conn.state["username"].startswith("guest_")

    @pytest.mark.asyncio
    async def test_on_connect_sends_welcome(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        await socket.on_connect(conn)

        # First send_json call should be the welcome message
        assert len(conn._sent_data) >= 1
        welcome = json.loads(conn._sent_data[0])
        assert welcome["type"] == "system"
        assert welcome["event"] == "welcome"
        assert "connection_id" in welcome["data"]

    @pytest.mark.asyncio
    async def test_on_connect_joins_general(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        await socket.on_connect(conn)

        assert "general" in conn.rooms

    @pytest.mark.asyncio
    async def test_on_connect_registers_presence(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        await socket.on_connect(conn)

        count = await socket.presence.get_online_count()
        assert count == 1


class TestChatSocketOnDisconnect:
    """Test ChatSocket.on_disconnect handler."""

    @pytest.mark.asyncio
    async def test_on_disconnect_accepts_reason(self):
        """on_disconnect must accept a reason parameter (the bug fix)."""
        socket = ChatSocket()
        socket.adapter = InMemoryAdapter()
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        conn.state["username"] = "alice"
        conn.state["rooms"] = set()  # empty so no room ops

        # Should NOT raise TypeError
        await socket.on_disconnect(conn, reason="client disconnect")

    @pytest.mark.asyncio
    async def test_on_disconnect_without_reason(self):
        """on_disconnect should also work without reason (default=None)."""
        socket = ChatSocket()
        socket.adapter = InMemoryAdapter()
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)
        conn.state["username"] = "alice"
        conn.state["rooms"] = set()

        await socket.on_disconnect(conn)

    @pytest.mark.asyncio
    async def test_on_disconnect_unregisters_presence(self):
        socket = ChatSocket()
        socket.adapter = InMemoryAdapter()
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)

        # Simulate connect then disconnect
        await socket.on_connect(conn)
        assert await socket.presence.get_online_count() == 1

        await socket.on_disconnect(conn, reason="test")
        assert await socket.presence.get_online_count() == 0


# ═════════════════════════════════════════════════════════════════════════════
#  ChatSocket event handler tests
# ═════════════════════════════════════════════════════════════════════════════


class TestChatSocketEvents:

    @pytest.fixture
    def socket(self):
        s = ChatSocket()
        s.adapter = InMemoryAdapter()
        return s

    @pytest.fixture
    async def conn(self):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        c = _make_connection(adapter=adapter)
        c.state["username"] = "alice"
        c.state["rooms"] = {"general"}
        return c

    @pytest.mark.asyncio
    async def test_set_username_success(self, socket, conn):
        result = await socket.set_username(conn, {"username": "Bob"})
        assert result["status"] == "ok"
        assert result["username"] == "Bob"
        assert conn.state["username"] == "Bob"

    @pytest.mark.asyncio
    async def test_set_username_empty(self, socket, conn):
        result = await socket.set_username(conn, {"username": ""})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_set_username_too_long(self, socket, conn):
        result = await socket.set_username(conn, {"username": "a" * 33})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_on_message_empty(self, socket, conn):
        """Empty message should send error via send_json."""
        await socket.on_message(conn, {"text": "", "room": "general"})
        # Should have sent an error message
        assert len(conn._sent_data) >= 1
        last = json.loads(conn._sent_data[-1])
        assert last["type"] == "error"

    @pytest.mark.asyncio
    async def test_on_message_too_long(self, socket, conn):
        """Message exceeding 2000 chars should send error."""
        await socket.on_message(conn, {"text": "x" * 2001, "room": "general"})
        last = json.loads(conn._sent_data[-1])
        assert last["type"] == "error"

    @pytest.mark.asyncio
    async def test_on_message_stores_history(self, socket, conn):
        await socket.on_message(conn, {"text": "Hello!", "room": "general"})
        history = await socket.messages.get_history("general")
        texts = [m["text"] for m in history]
        assert "Hello!" in texts

    @pytest.mark.asyncio
    async def test_join_room_success(self, socket, conn):
        result = await socket.join_room(conn, {"room": "random"})
        assert result["status"] == "ok"
        assert "random" in conn.state["rooms"]

    @pytest.mark.asyncio
    async def test_join_room_empty_name(self, socket, conn):
        result = await socket.join_room(conn, {"room": ""})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_join_room_already_joined(self, socket, conn):
        result = await socket.join_room(conn, {"room": "general"})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_leave_room_success(self, socket, conn):
        # First join a non-general room
        await conn.join_room("tech")
        conn.state["rooms"].add("tech")
        result = await socket.leave_room(conn, {"room": "tech"})
        assert result["status"] == "ok"
        assert "tech" not in conn.state["rooms"]

    @pytest.mark.asyncio
    async def test_leave_room_general_blocked(self, socket, conn):
        result = await socket.leave_room(conn, {"room": "general"})
        assert result["status"] == "error"
        assert "Cannot leave" in result["message"]

    @pytest.mark.asyncio
    async def test_leave_room_not_joined(self, socket, conn):
        result = await socket.leave_room(conn, {"room": "nonexistent"})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_list_rooms(self, socket, conn):
        result = await socket.list_rooms(conn, {})
        assert result["status"] == "ok"
        assert "joined_rooms" in result
        assert "available_rooms" in result


# ═════════════════════════════════════════════════════════════════════════════
#  NotificationSocket tests
# ═════════════════════════════════════════════════════════════════════════════


class TestNotificationSocket:

    @pytest.fixture
    def socket(self):
        s = NotificationSocket()
        s.adapter = InMemoryAdapter()
        return s

    @pytest.mark.asyncio
    async def test_on_connect(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(namespace="/notifications", adapter=adapter)
        await socket.on_connect(conn)
        assert "subscriptions" in conn.state
        # Should have sent a connected message
        assert len(conn._sent_data) >= 1
        msg = json.loads(conn._sent_data[0])
        assert msg["event"] == "connected"

    @pytest.mark.asyncio
    async def test_on_disconnect_with_reason(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(namespace="/notifications", adapter=adapter)
        # Should not raise
        await socket.on_disconnect(conn, reason="gone")

    @pytest.mark.asyncio
    async def test_subscribe_topic(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(namespace="/notifications", adapter=adapter)
        conn.state["subscriptions"] = set()

        result = await socket.subscribe_topic(conn, {"topic": "orders"})
        assert result["status"] == "ok"
        assert "orders" in conn.state["subscriptions"]

    @pytest.mark.asyncio
    async def test_subscribe_empty_topic(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(namespace="/notifications", adapter=adapter)
        conn.state["subscriptions"] = set()

        result = await socket.subscribe_topic(conn, {"topic": ""})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_unsubscribe_topic(self, socket):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(namespace="/notifications", adapter=adapter)
        conn.state["subscriptions"] = {"orders"}

        result = await socket.unsubscribe_topic(conn, {"topic": "orders"})
        assert result["status"] == "ok"
        assert "orders" not in conn.state["subscriptions"]


# ═════════════════════════════════════════════════════════════════════════════
#  publish_room with exclude_connection
# ═════════════════════════════════════════════════════════════════════════════


class TestPublishRoomExclude:
    """Verify publish_room exclude_connection support end-to-end."""

    @pytest.mark.asyncio
    async def test_exclude_connection_skips_sender(self):
        adapter = InMemoryAdapter()
        await adapter.initialize()

        conn_a = _make_connection(connection_id="conn-a", adapter=adapter)
        conn_b = _make_connection(connection_id="conn-b", adapter=adapter)

        ns = "/chat"

        # Register connections and callbacks with the adapter
        await adapter.register_connection(ns, "conn-a", "w1")
        await adapter.register_connection(ns, "conn-b", "w1")
        adapter.register_send_callback(ns, "conn-a", conn_a._send_func)
        adapter.register_send_callback(ns, "conn-b", conn_b._send_func)

        # Both join room
        await adapter.join_room(ns, "general", "conn-a")
        await adapter.join_room(ns, "general", "conn-b")

        # Publish excluding conn-a
        envelope = MessageEnvelope(
            type=MessageType.EVENT,
            event="test",
            payload={"msg": "hi"},
        )
        await adapter.publish(ns, "general", envelope, exclude_connection="conn-a")

        # conn-a should NOT have received the message
        assert len(conn_a._sent_data) == 0
        # conn-b SHOULD have received it
        assert len(conn_b._sent_data) == 1

    @pytest.mark.asyncio
    async def test_publish_room_controller_method(self):
        """Test SocketController.publish_room with exclude_connection kwarg."""
        adapter = InMemoryAdapter()
        await adapter.initialize()

        # Create controller with adapter
        ctrl = SocketController()
        ctrl.namespace = "/chat"
        ctrl.adapter = adapter

        conn_a = _make_connection(connection_id="conn-a", adapter=adapter)
        conn_b = _make_connection(connection_id="conn-b", adapter=adapter)

        ns = "/chat"
        await adapter.register_connection(ns, "conn-a", "w1")
        await adapter.register_connection(ns, "conn-b", "w1")
        adapter.register_send_callback(ns, "conn-a", conn_a._send_func)
        adapter.register_send_callback(ns, "conn-b", conn_b._send_func)
        await adapter.join_room(ns, "general", "conn-a")
        await adapter.join_room(ns, "general", "conn-b")

        await ctrl.publish_room(
            "general", "user_joined", {"user": "alice"},
            exclude_connection="conn-a",
        )

        assert len(conn_a._sent_data) == 0
        assert len(conn_b._sent_data) == 1


# ═════════════════════════════════════════════════════════════════════════════
#  Runtime _call_on_disconnect signature introspection
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeOnDisconnectIntrospection:
    """_call_on_disconnect should handle handlers with and without reason."""

    @pytest.mark.asyncio
    async def test_handler_with_reason(self):
        """Handler accepting reason should receive it."""
        received = {}

        @Socket("/test")
        class TestSocket(SocketController):
            namespace = "/test"

            @OnDisconnect()
            async def on_disconnect(self, conn, reason=None):
                received["reason"] = reason

        router = SocketRouter()
        runtime = AquilaSockets(router=router, adapter=InMemoryAdapter())
        ctrl = TestSocket()

        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(namespace="/test", adapter=adapter)

        await runtime._call_on_disconnect(ctrl, conn, "server shutdown")
        assert received["reason"] == "server shutdown"

    @pytest.mark.asyncio
    async def test_handler_without_reason(self):
        """Handler NOT accepting reason should still work (no TypeError)."""
        called = {"yes": False}

        @Socket("/test2")
        class TestSocket2(SocketController):
            namespace = "/test2"

            @OnDisconnect()
            async def on_disconnect(self, conn):
                called["yes"] = True

        router = SocketRouter()
        runtime = AquilaSockets(router=router, adapter=InMemoryAdapter())
        ctrl = TestSocket2()

        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(namespace="/test2", adapter=adapter)

        # This was the original bug — should NOT raise TypeError
        await runtime._call_on_disconnect(ctrl, conn, "test reason")
        assert called["yes"] is True


# ═════════════════════════════════════════════════════════════════════════════
#  ChatController HTTP tests
# ═════════════════════════════════════════════════════════════════════════════


class TestChatController:
    """Test ChatController HTTP endpoints via direct method calls."""

    @pytest.fixture
    def ctrl(self):
        from myapp.modules.chat.controllers import ChatController
        return ChatController()

    def _make_ctx(self, path="/chat", method="GET", body=None, query_params=None):
        """Build a minimal RequestCtx mock."""
        from aquilia.controller.base import RequestCtx
        request = MagicMock()
        request.path = path
        request.method = method
        request.headers = {}
        request.query_params = query_params or {}
        request.state = {}

        async def _json():
            return body or {}

        request.json = _json

        ctx = RequestCtx(request=request)

        async def ctx_json():
            return body or {}

        ctx.json = ctx_json
        return ctx

    @pytest.mark.asyncio
    async def test_list_rooms(self, ctrl):
        ctx = self._make_ctx()
        resp = await ctrl.list_rooms(ctx)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_create_room(self, ctrl):
        ctx = self._make_ctx(body={"name": "Test Room", "description": "A test"})
        resp = await ctrl.create_room(ctx)
        assert resp.status == 201

    @pytest.mark.asyncio
    async def test_create_room_empty_name(self, ctrl):
        ctx = self._make_ctx(body={"name": ""})
        resp = await ctrl.create_room(ctx)
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_get_online_users(self, ctrl):
        ctx = self._make_ctx()
        resp = await ctrl.get_online_users(ctx)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_get_stats(self, ctrl):
        ctx = self._make_ctx()
        resp = await ctrl.get_stats(ctx)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_get_messages(self, ctrl):
        ctx = self._make_ctx(query_params={"limit": "10"})
        resp = await ctrl.get_messages(ctx, room_id="general")
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_delete_room_missing(self, ctrl):
        ctx = self._make_ctx()
        resp = await ctrl.delete_room(ctx, room_id="nonexistent")
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_chat_index_without_templates(self, ctrl):
        """Without template engine, should return fallback HTML."""
        ctx = self._make_ctx()
        resp = await ctrl.chat_index(ctx)
        assert resp.status == 200


# ═════════════════════════════════════════════════════════════════════════════
#  MessageEnvelope dual-format parsing
# ═════════════════════════════════════════════════════════════════════════════


class TestEnvelopeDualFormat:
    """Ensure from_dict accepts both protocol ('payload') and client ('data') keys."""

    def test_protocol_format_with_payload(self):
        """Standard protocol format: {'event': '...', 'payload': {...}}."""
        env = MessageEnvelope.from_dict({
            "event": "message",
            "payload": {"text": "hello"},
        })
        assert env.payload == {"text": "hello"}

    def test_client_format_with_data(self):
        """Browser client format: {'event': '...', 'data': {...}}."""
        env = MessageEnvelope.from_dict({
            "event": "message",
            "data": {"text": "world"},
        })
        assert env.payload == {"text": "world"}

    def test_payload_takes_priority_over_data(self):
        """When both 'payload' and 'data' present, 'payload' wins."""
        env = MessageEnvelope.from_dict({
            "event": "test",
            "payload": {"from": "protocol"},
            "data": {"from": "client"},
        })
        assert env.payload == {"from": "protocol"}

    def test_empty_when_neither_present(self):
        """Defaults to {} when neither 'payload' nor 'data' are present."""
        env = MessageEnvelope.from_dict({"event": "ping"})
        assert env.payload == {}

    def test_ack_field_parsed(self):
        """Client can request ack via 'ack': true."""
        env = MessageEnvelope.from_dict({
            "event": "join_room",
            "data": {"room": "general"},
            "ack": True,
        })
        assert env.ack is True
        assert env.payload == {"room": "general"}


# ═════════════════════════════════════════════════════════════════════════════
#  AckEvent dispatch logic
# ═════════════════════════════════════════════════════════════════════════════


class TestAckEventDispatch:
    """Ensure @AckEvent handler results are sent back even without client ack flag."""

    @pytest.mark.asyncio
    async def test_ack_event_sends_result_without_client_ack(self):
        """@AckEvent handlers should send result via send_json even when
        client doesn't set ack=True."""
        @Socket("/acktest")
        class AckTestSocket(SocketController):
            namespace = "/acktest"

            @AckEvent("ping")
            async def handle_ping(self, conn, data):
                return {"status": "ok", "pong": True}

        router = SocketRouter()
        adapter = InMemoryAdapter()
        await adapter.initialize()
        runtime = AquilaSockets(router=router, adapter=adapter)
        ctrl = AckTestSocket()
        ctrl.namespace = "/acktest"
        ctrl.adapter = adapter
        runtime.controller_instances["/acktest"] = ctrl

        conn = _make_connection(namespace="/acktest", adapter=adapter)

        # Client message WITHOUT ack=True
        envelope = MessageEnvelope.from_dict({
            "event": "ping",
            "data": {},
        })

        await runtime._dispatch_event(conn, ctrl, envelope)

        # The handler returned a dict → should have been sent via send_json
        assert len(conn._sent_data) == 1
        sent = json.loads(conn._sent_data[0].decode("utf-8") if isinstance(conn._sent_data[0], bytes) else conn._sent_data[0])
        assert sent["status"] == "ok"
        assert sent["pong"] is True


# ═════════════════════════════════════════════════════════════════════════════
#  send_envelope metrics tracking
# ═════════════════════════════════════════════════════════════════════════════


class TestSendEnvelopeMetrics:
    """Ensure send_envelope tracks bytes_sent and last_activity."""

    @pytest.mark.asyncio
    async def test_send_envelope_tracks_bytes(self):
        adapter = InMemoryAdapter()
        await adapter.initialize()
        conn = _make_connection(adapter=adapter)

        initial_bytes = conn.bytes_sent
        initial_msgs = conn.messages_sent

        envelope = MessageEnvelope(
            type=MessageType.EVENT,
            event="test",
            payload={"hello": "world"},
        )
        await conn.send_envelope(envelope)

        assert conn.messages_sent == initial_msgs + 1
        assert conn.bytes_sent > initial_bytes
        assert conn.last_activity is not None


# ═════════════════════════════════════════════════════════════════════════════
#  AquilaSockets lifecycle (initialize/shutdown)
# ═════════════════════════════════════════════════════════════════════════════


class TestAquilaSocketsLifecycle:
    """Ensure initialize() and shutdown() are properly wired."""

    @pytest.mark.asyncio
    async def test_initialize_marks_ready(self):
        router = SocketRouter()
        adapter = InMemoryAdapter()
        runtime = AquilaSockets(router=router, adapter=adapter)

        assert not runtime._initialized
        await runtime.initialize()
        assert runtime._initialized
        await runtime.shutdown()
        assert not runtime._initialized

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_all(self):
        router = SocketRouter()
        adapter = InMemoryAdapter()
        await adapter.initialize()
        runtime = AquilaSockets(router=router, adapter=adapter)
        await runtime.initialize()

        # Register a fake connection
        conn = _make_connection(adapter=adapter)
        conn.mark_connected()
        runtime.connections[conn.connection_id] = conn
        await adapter.register_connection("/chat", conn.connection_id, "w1")

        await runtime.shutdown()
        assert len(runtime.connections) == 0


# ═════════════════════════════════════════════════════════════════════════════
#  Message loop text frame handling
# ═════════════════════════════════════════════════════════════════════════════


class TestMessageLoopTextFrames:
    """Ensure the runtime handles text WebSocket frames (not just binary)."""

    @pytest.mark.asyncio
    async def test_text_frame_dispatched(self):
        """A text frame with JSON should be decoded and dispatched."""
        handled = {"event": None, "payload": None}

        @Socket("/texttest")
        class TextTestSocket(SocketController):
            namespace = "/texttest"

            @Event("greet")
            async def handle_greet(self, conn, data):
                handled["event"] = "greet"
                handled["payload"] = data

        router = SocketRouter()
        adapter = InMemoryAdapter()
        await adapter.initialize()
        runtime = AquilaSockets(router=router, adapter=adapter)
        ctrl = TextTestSocket()
        ctrl.namespace = "/texttest"
        ctrl.adapter = adapter
        runtime.controller_instances["/texttest"] = ctrl

        conn = _make_connection(namespace="/texttest", adapter=adapter)

        # Simulate what the runtime's _handle_message receives: bytes
        text_msg = json.dumps({"event": "greet", "data": {"name": "Alice"}})
        await runtime._handle_message(conn, ctrl, text_msg.encode("utf-8"))

        assert handled["event"] == "greet"
        assert handled["payload"] == {"name": "Alice"}
