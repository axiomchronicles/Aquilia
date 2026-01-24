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
]

__version__ = "0.1.0"
