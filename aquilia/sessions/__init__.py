"""
AquilaSessions - Production-grade session management for Aquilia.

This package provides explicit, policy-driven session management with:
- Cryptographic session IDs
- Multiple backend stores (memory, Redis, file)
- Policy-based lifecycle management
- Transport-agnostic design (HTTP, WebSocket, etc.)
- Deep integration with Aquilia's DI, Flow, and Faults systems

Philosophy:
- Sessions are capabilities (grant scoped access)
- Sessions are explicit (no hidden globals)
- Sessions are policy-driven (declared behavior)
- Sessions are observable (auditable mutations)
- Sessions are transport-agnostic (not tied to cookies)
"""

from .core import (
    Session,
    SessionID,
    SessionPrincipal,
    SessionScope,
    SessionFlag,
)

from .policy import (
    SessionPolicy,
    PersistencePolicy,
    ConcurrencyPolicy,
    TransportPolicy,
)

from .store import (
    MemoryStore,
    FileStore,
)

from .transport import (
    CookieTransport,
    HeaderTransport,
    create_transport,
)

from .engine import SessionEngine

from .faults import (
    SessionFault,
    SessionExpiredFault,
    SessionInvalidFault,
    SessionConcurrencyViolationFault,
    SessionStoreUnavailableFault,
    SessionRotationFailedFault,
    SessionPolicyViolationFault,
)

# Unique Aquilia session syntax (NEW)
from .decorators import (
    session,
    authenticated,
    stateful,
    SessionRequiredFault,
    AuthenticationRequiredFault,
)

from .state import (
    SessionState,
    Field,
    CartState,
    UserPreferencesState,
)

from .enhanced import (
    SessionContext,
    SessionGuard,
    requires,
    AdminGuard,
    VerifiedEmailGuard,
)

__all__ = [
    # Core types
    "Session",
    "SessionID",
    "SessionPrincipal",
    "SessionScope",
    "SessionFlag",
    # Policy types
    "SessionPolicy",
    "PersistencePolicy",
    "ConcurrencyPolicy",
    "TransportPolicy",
    # Engine
    "SessionEngine",
    # Storage
    "SessionStore",
    "MemoryStore",
    "FileStore",
    # Transport
    "SessionTransport",
    "CookieTransport",
    "HeaderTransport",
    # Faults
    "SessionFault",
    "SessionExpiredFault",
    "SessionInvalidFault",
    "SessionConcurrencyViolationFault",
    "SessionStoreUnavailableFault",
    "SessionRotationFailedFault",
    "SessionPolicyViolationFault",
    # Decorators (NEW - Unique syntax)
    "session",
    "authenticated",
    "stateful",
    "SessionRequiredFault",
    "AuthenticationRequiredFault",
    # State (NEW - Typed state)
    "SessionState",
    "Field",
    "CartState",
    "UserPreferencesState",
    # Enhanced features (NEW - Advanced patterns)
    "SessionContext",
    "SessionGuard",
    "requires",
    "AdminGuard",
    "VerifiedEmailGuard",
]

__version__ = "0.1.0"
