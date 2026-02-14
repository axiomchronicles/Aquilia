"""
WebSocket Runtime - ASGI integration and connection management

Integrates WebSocket controllers with Aquilia's ASGI adapter.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set, Callable
from dataclasses import dataclass
import logging
import uuid
import asyncio

from .connection import Connection, ConnectionScope, ConnectionState
from .controller import SocketController
from .envelope import MessageEnvelope, MessageType, JSONCodec
from .faults import (
    WS_HANDSHAKE_FAILED,
    WS_MESSAGE_INVALID,
    WS_CONNECTION_CLOSED,
    WS_UNSUPPORTED_EVENT,
)
from .guards import SocketGuard
from .middleware import MiddlewareChain, MessageHandler
from .adapters import Adapter, InMemoryAdapter

from aquilia.faults import Fault
from aquilia.auth.core import Identity
from aquilia.sessions.core import Session

logger = logging.getLogger("aquilia.sockets.runtime")


@dataclass
class RouteMetadata:
    """Socket route metadata extracted from controller."""
    namespace: str
    path_pattern: str
    controller_class: type[SocketController]
    handlers: Dict[str, Callable]  # event -> method
    schemas: Dict[str, Any]  # event -> schema
    guards: list[SocketGuard]
    allowed_origins: Optional[list[str]]
    max_connections: Optional[int]
    message_rate_limit: Optional[int]
    max_message_size: int


class SocketRouter:
    """
    Router for WebSocket namespaces.
    
    Matches paths to controllers and manages routing.
    """
    
    def __init__(self):
        """Initialize socket router."""
        self.routes: Dict[str, RouteMetadata] = {}  # namespace -> metadata
        self._compiled_patterns: Dict[str, Any] = {}  # namespace -> CompiledPattern
        try:
            from aquilia.patterns import PatternCompiler, PatternMatcher
            self._pattern_compiler = PatternCompiler()
            self._pattern_matcher = PatternMatcher()
            self._has_patterns = True
        except ImportError:
            self._pattern_compiler = None
            self._pattern_matcher = None
            self._has_patterns = False
    
    def register(
        self,
        namespace: str,
        metadata: RouteMetadata,
    ):
        """
        Register socket controller.
        
        Args:
            namespace: Namespace identifier
            metadata: Route metadata
        """
        if namespace in self.routes:
            logger.warning(f"Namespace {namespace} already registered, overwriting")
        
        self.routes[namespace] = metadata
        
        # Pre-compile pattern for fast matching
        if self._has_patterns and self._pattern_compiler:
            try:
                compiled = self._pattern_compiler.compile(metadata.path_pattern)
                self._compiled_patterns[namespace] = compiled
            except Exception as e:
                logger.debug(f"Could not compile pattern for {namespace}: {e}")
        
        logger.info(f"Registered WebSocket namespace: {namespace}")
    
    def match(self, path: str) -> Optional[tuple[str, RouteMetadata, Dict[str, Any]]]:
        """
        Match path to namespace.
        
        Args:
            path: Request path
            
        Returns:
            (namespace, metadata, path_params) or None
        """
        # Use Aquilia's PatternMatcher if available for full pattern support
        if self._has_patterns and self._pattern_matcher:
            for namespace, metadata in self.routes.items():
                compiled = self._compiled_patterns.get(namespace)
                if compiled:
                    try:
                        result = self._pattern_matcher.match(compiled, path)
                        if result and result.matched:
                            return (namespace, metadata, result.params or {})
                    except Exception:
                        pass  # Fall through to basic matching
                # Fallback: exact match
                if metadata.path_pattern == path:
                    return (namespace, metadata, {})
            return None
        
        # Fallback: basic matching without Patterns subsystem
        for namespace, metadata in self.routes.items():
            pattern = metadata.path_pattern
            
            # Simple static matching
            if pattern == path:
                return (namespace, metadata, {})
            
            # Basic param matching (e.g., /chat/:namespace)
            if ":" in pattern:
                parts = pattern.split("/")
                path_parts = path.split("/")
                
                if len(parts) == len(path_parts):
                    params = {}
                    match = True
                    
                    for i, part in enumerate(parts):
                        if part.startswith(":"):
                            param_name = part[1:]
                            params[param_name] = path_parts[i]
                        elif part != path_parts[i]:
                            match = False
                            break
                    
                    if match:
                        return (namespace, metadata, params)
        
        return None


class AquilaSockets:
    """
    Main WebSocket runtime.
    
    Manages:
    - Connection lifecycle
    - Message routing
    - Controller execution
    - DI integration
    """
    
    def __init__(
        self,
        router: SocketRouter,
        adapter: Optional[Adapter] = None,
        container_factory: Optional[Callable] = None,
        auth_manager: Optional[Any] = None,
        session_engine: Optional[Any] = None,
    ):
        """
        Initialize WebSocket runtime.
        
        Args:
            router: Socket router
            adapter: Scaling adapter (default: InMemoryAdapter)
            container_factory: Factory for creating DI containers
            auth_manager: Auth manager for handshake auth
            session_engine: Session engine for session support
        """
        self.router = router
        self.adapter = adapter or InMemoryAdapter()
        self.container_factory = container_factory
        self.auth_manager = auth_manager
        self.session_engine = session_engine
        
        self.connections: Dict[str, Connection] = {}
        self.controller_instances: Dict[str, SocketController] = {}
        
        self.codec = JSONCodec()
        self._initialized = False
    
    async def initialize(self):
        """Initialize runtime."""
        await self.adapter.initialize()
        self._initialized = True
        logger.info("AquilaSockets initialized")
    
    async def shutdown(self):
        """Shutdown runtime."""
        # Disconnect all connections
        for conn in list(self.connections.values()):
            await self._disconnect_connection(conn, "server shutdown")
        
        await self.adapter.shutdown()
        self._initialized = False
        logger.info("AquilaSockets shut down")
    
    async def handle_websocket(self, scope: dict, receive: callable, send: callable):
        """
        Handle WebSocket connection (ASGI entry point).
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Match route
        path = scope.get("path", "/")
        match_result = self.router.match(path)
        
        if not match_result:
            # No route found - reject handshake
            await send({
                "type": "websocket.close",
                "code": 1003,
                "reason": "No matching WebSocket namespace",
            })
            return
        
        namespace, route_metadata, path_params = match_result
        
        # Perform handshake
        try:
            conn = await self._perform_handshake(
                scope,
                send,
                namespace,
                route_metadata,
                path_params,
            )
        except Fault as e:
            logger.warning(f"Handshake failed: {e.message}")
            await send({
                "type": "websocket.close",
                "code": getattr(e, "ws_close_code", 1003),
                "reason": e.message[:123],  # Max 123 bytes
            })
            return
        
        # Accept connection
        await send({"type": "websocket.accept"})
        conn.mark_connected()
        
        # Call on_connect handler
        controller = self.controller_instances.get(namespace)
        if controller:
            try:
                await self._call_on_connect(controller, conn)
            except Fault as e:
                logger.error(f"OnConnect handler failed: {e.message}")
                await self._disconnect_connection(conn, e.message)
                return
            except Exception as e:
                logger.error(f"OnConnect unexpected error: {e}", exc_info=True)
                await self._disconnect_connection(conn, str(e))
                return
        
        # Message loop
        await self._message_loop(conn, controller, receive, send)
    
    async def _perform_handshake(
        self,
        scope: dict,
        send: callable,
        namespace: str,
        route_metadata: RouteMetadata,
        path_params: Dict[str, Any],
    ) -> Connection:
        """Perform WebSocket handshake."""
        # Create Request object for robust parsing
        from aquilia.request import Request
        
        # Mock receive that returns nothing (we don't read body in handshake)
        async def mock_receive(): return {"type": "websocket.receive", "bytes": b""}
        
        # Create request with websocket scope
        # We temporarily treat it as HTTP-like for parsing helpers
        req = Request(scope, mock_receive)
        
        # Extract parsing results from Request
        headers = dict(req.headers)
        query_params = dict(req.query_params)
        
        conn_scope = ConnectionScope(
            namespace=namespace,
            path=req.path,
            path_params=path_params,
            query_params=query_params,
            headers=headers,
        )
        
        logger.info(f"Handshake starting for {namespace} path={req.path}")
        
        # Authenticate using the robust Request object
        identity, session = await self._authenticate_handshake(req)
        logger.info(f"Auth result: identity={identity}, session={session}")
        
        # Run guards
        for guard in route_metadata.guards:
            await guard.check_handshake(conn_scope, identity, session)
        
        # Check origin
        if route_metadata.allowed_origins:
            origin = headers.get("origin", "")
            logger.info(f"Checking origin: {origin} vs {route_metadata.allowed_origins}")
            if origin and origin not in route_metadata.allowed_origins:
                from .faults import WS_ORIGIN_NOT_ALLOWED
                raise WS_ORIGIN_NOT_ALLOWED(origin)
        
        # Create DI container
        container = None
        if self.container_factory:
            # Pass request context if factory supports it
            try:
                container = await self.container_factory(req)
            except TypeError:
                container = await self.container_factory()
        
        # Create connection
        connection_id = str(uuid.uuid4())
        
        async def send_func(data: bytes):
            await send({
                "type": "websocket.send",
                "bytes": data,
            })
        
        conn = Connection(
            connection_id=connection_id,
            namespace=namespace,
            scope=conn_scope,
            container=container,
            adapter=self.adapter,
            send_func=send_func,
            identity=identity,
            session=session,
        )
        
        # Register connection
        self.connections[connection_id] = conn
        
        # Register with adapter
        await self.adapter.register_connection(
            namespace=namespace,
            connection_id=connection_id,
            worker_id="worker-1",  # TODO: Get actual worker ID
        )
        
        # Register send callback with adapter (for InMemoryAdapter)
        if hasattr(self.adapter, "register_send_callback"):
            self.adapter.register_send_callback(namespace, connection_id, send_func)
        
        logger.info(f"Handshake successful: {connection_id} ({namespace})")
        
        return conn
    
    async def _authenticate_handshake(
        self,
        request: "Request",
    ) -> tuple[Optional[Identity], Optional[Session]]:
        """
        Authenticate handshake using Request object.
        
        Tries multiple auth methods:
        1. Authorization header (via Request helper)
        2. Query string token (?token=...)
        3. Session cookie (via SessionEngine)
        
        Returns:
            (identity, session) tuple
        """
        identity = None
        session = None
        
        
        # 1. Try Authorization header
        # Using Request's auth_scheme/auth_credentials
        scheme = request.auth_scheme()
        credentials = request.auth_credentials()
        
        if scheme and scheme.lower() == "bearer" and credentials and self.auth_manager:
            try:
                identity = await self.auth_manager.get_identity_from_token(credentials)
            except Exception as e:
                logger.debug(f"Token auth failed: {e}")
        
        # 2. Try query string token
        if not identity and self.auth_manager:
            token = request.query_param("token")
            if token:
                try:
                    identity = await self.auth_manager.get_identity_from_token(token)
                except Exception as e:
                    logger.debug(f"Query token auth failed: {e}")
        
        # 3. Try session cookie (Unified with HTTP flow)
        if self.session_engine:
            try:
                # Use SessionEngine to load session from request
                # This uses the same logic as SessionMiddleware
                # Note: Pass None for container as we prefer to register it later strictly
                session = await self.session_engine.resolve(request, None)
                
                if session and not identity:
                    # Extract identity from session
                    # We can use the standard session helper since we have a real Session object
                    if "identity_id" in session.data and self.auth_manager:
                        identity_id = session.data["identity_id"]
                        identity = await self.auth_manager.identity_store.get(identity_id)
                        
            except Exception as e:
                logger.debug(f"Session auth failed: {e}")
        
        return identity, session
    
    async def _call_on_connect(self, controller: SocketController, conn: Connection):
        """Call controller's on_connect handler."""
        # Find @OnConnect handler
        for name, method in controller.__class__.__dict__.items():
            if hasattr(method, "__socket_handler__"):
                metadata = method.__socket_handler__
                if metadata.get("type") == "on_connect":
                    await method(controller, conn)
                    return
    
    async def _message_loop(
        self,
        conn: Connection,
        controller: Optional[SocketController],
        receive: callable,
        send: callable,
    ):
        """Message receive loop."""
        try:
            while conn.is_connected:
                message = await receive()
                
                if message["type"] == "websocket.receive":
                    # Handle text or binary message
                    data = message.get("bytes") or message.get("text", "").encode("utf-8")
                    
                    if data:
                        conn.record_received(len(data))
                        await self._handle_message(conn, controller, data)
                
                elif message["type"] == "websocket.disconnect":
                    # Client disconnected
                    code = message.get("code", 1000)
                    await self._disconnect_connection(conn, f"client disconnect (code {code})")
                    break
        
        except Exception as e:
            logger.error(f"Message loop error: {e}", exc_info=True)
            await self._disconnect_connection(conn, f"error: {e}")
    
    async def _handle_message(
        self,
        conn: Connection,
        controller: Optional[SocketController],
        data: bytes,
    ):
        """Handle incoming message."""
        try:
            # Decode envelope
            envelope = self.codec.decode(data)
            
            # Route to controller handler
            if controller:
                await self._dispatch_event(conn, controller, envelope)
        
        except Exception as e:
            logger.error(f"Message handling error: {e}", exc_info=True)
            
            # Send error ack if message had ID
            # await conn.send_ack(envelope.id, status="error", error=str(e))
    
    async def _dispatch_event(
        self,
        conn: Connection,
        controller: SocketController,
        envelope: MessageEnvelope,
    ):
        """Dispatch event to controller handler."""
        event = envelope.event
        
        # Find handler
        for name, method in controller.__class__.__dict__.items():
            if hasattr(method, "__socket_handler__"):
                metadata = method.__socket_handler__
                
                if metadata.get("event") == event:
                    # Validate schema
                    schema = metadata.get("schema")
                    if schema:
                        valid, error = schema.validate(envelope.payload)
                        if not valid:
                            raise WS_MESSAGE_INVALID(error)
                    
                    # Call handler
                    result = await method(controller, conn, envelope.payload)
                    
                    # Send ack if requested
                    if envelope.ack:
                        await conn.send_ack(
                            envelope.id,
                            status="ok",
                            data=result if isinstance(result, dict) else {},
                        )
                    
                    return
        
        # No handler found
        logger.warning(f"No handler for event: {event}")
        raise WS_UNSUPPORTED_EVENT(event)
    
    async def _disconnect_connection(self, conn: Connection, reason: str):
        """Disconnect connection."""
        if conn.connection_id not in self.connections:
            return
        
        conn.mark_closing()
        
        # Call on_disconnect handler
        controller = self.controller_instances.get(conn.namespace)
        if controller:
            try:
                await self._call_on_disconnect(controller, conn, reason)
            except Exception as e:
                logger.error(f"OnDisconnect handler error: {e}", exc_info=True)
        
        # Cleanup
        await conn.leave_all()
        
        if hasattr(self.adapter, "unregister_send_callback"):
            self.adapter.unregister_send_callback(conn.namespace, conn.connection_id)
        
        await self.adapter.unregister_connection(conn.namespace, conn.connection_id)
        
        del self.connections[conn.connection_id]
        
        conn.mark_closed()
        
        logger.info(f"Connection closed: {conn.connection_id} ({reason})")
    
    async def _call_on_disconnect(
        self,
        controller: SocketController,
        conn: Connection,
        reason: Optional[str],
    ):
        """Call controller's on_disconnect handler."""
        for name, method in controller.__class__.__dict__.items():
            if hasattr(method, "__socket_handler__"):
                metadata = method.__socket_handler__
                if metadata.get("type") == "on_disconnect":
                    await method(controller, conn, reason)
                    return
