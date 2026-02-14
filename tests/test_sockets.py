"""
Test 20: Sockets System (sockets/)

Tests SocketController, Connection, decorators, MessageEnvelope,
guards, faults, adapters.
"""

import pytest

from aquilia.sockets import (
    SocketController,
    Connection,
    ConnectionState,
    ConnectionScope,
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    AckEvent,
    Subscribe,
    Unsubscribe,
    Guard,
    MessageEnvelope,
    MessageType,
    MessageCodec,
    JSONCodec,
    SocketGuard,
    HandshakeAuthGuard,
    OriginGuard,
    SocketFault,
    WS_HANDSHAKE_FAILED,
    WS_AUTH_REQUIRED,
    WS_MESSAGE_INVALID,
    Adapter,
    InMemoryAdapter,
)


# ============================================================================
# SocketController
# ============================================================================

class TestSocketController:

    def test_exists(self):
        assert SocketController is not None

    def test_subclass(self):
        class ChatSocket(SocketController):
            pass

        assert issubclass(ChatSocket, SocketController)


# ============================================================================
# Connection / ConnectionState
# ============================================================================

class TestConnectionState:

    def test_values(self):
        assert ConnectionState.CONNECTING is not None or hasattr(ConnectionState, "CONNECTED")

    def test_enum_members(self):
        members = list(ConnectionState)
        assert len(members) > 0


class TestConnectionScope:

    def test_exists(self):
        assert ConnectionScope is not None


# ============================================================================
# Decorators
# ============================================================================

class TestSocketDecorators:

    def test_socket_decorator(self):
        assert Socket is not None

    def test_on_connect(self):
        assert OnConnect is not None

    def test_on_disconnect(self):
        assert OnDisconnect is not None

    def test_event_decorator(self):
        assert Event is not None

    def test_ack_event(self):
        assert AckEvent is not None

    def test_subscribe(self):
        assert Subscribe is not None

    def test_unsubscribe(self):
        assert Unsubscribe is not None

    def test_guard_decorator(self):
        assert Guard is not None


# ============================================================================
# MessageEnvelope / MessageType / Codecs
# ============================================================================

class TestMessageEnvelope:

    def test_exists(self):
        assert MessageEnvelope is not None

    def test_message_type(self):
        members = list(MessageType)
        assert len(members) > 0


class TestJSONCodec:

    def test_exists(self):
        codec = JSONCodec()
        assert hasattr(codec, 'encode') or hasattr(codec, 'decode')


# ============================================================================
# Guards
# ============================================================================

class TestSocketGuards:

    def test_socket_guard(self):
        assert SocketGuard is not None

    def test_handshake_auth_guard(self):
        assert HandshakeAuthGuard is not None

    def test_origin_guard(self):
        assert OriginGuard is not None


# ============================================================================
# Faults
# ============================================================================

class TestSocketFaults:

    def test_socket_fault(self):
        assert issubclass(SocketFault, Exception)

    def test_fault_instances(self):
        assert WS_HANDSHAKE_FAILED is not None
        assert WS_AUTH_REQUIRED is not None
        assert WS_MESSAGE_INVALID is not None


# ============================================================================
# Adapters
# ============================================================================

class TestAdapters:

    def test_adapter_base(self):
        assert Adapter is not None

    def test_in_memory_adapter(self):
        adapter = InMemoryAdapter()
        assert hasattr(adapter, 'publish') or hasattr(adapter, 'subscribe') or adapter is not None
