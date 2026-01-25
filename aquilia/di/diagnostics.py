"""
DI Diagnostics - Observability and event tracking for DI containers.
"""

import time
from typing import Any, Dict, List, Optional, Type, Protocol
from enum import Enum
import dataclasses
import logging

logger = logging.getLogger("aquilia.di.diagnostics")

class DIEventType(Enum):
    """Types of DI events."""
    REGISTRATION = "registration"
    RESOLUTION_START = "resolution_start"
    RESOLUTION_SUCCESS = "resolution_success"
    RESOLUTION_FAILURE = "resolution_failure"
    LIFECYCLE_STARTUP = "lifecycle_startup"
    LIFECYCLE_SHUTDOWN = "lifecycle_shutdown"
    PROVIDER_INSTANTATION = "provider_instantiation"

@dataclasses.dataclass
class DIEvent:
    """A diagnostic event in the DI system."""
    type: DIEventType
    timestamp: float = dataclasses.field(default_factory=time.time)
    token: Optional[Any] = None
    tag: Optional[str] = None
    provider_name: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

class DiagnosticListener(Protocol):
    """Interface for DI diagnostic listeners."""
    def on_event(self, event: DIEvent) -> None:
        """Called when a DI event occurs."""
        ...

class ConsoleDiagnosticListener:
    """Simple diagnostic listener that logs to console/logging."""
    def __init__(self, log_level: int = logging.DEBUG):
        self.log_level = log_level

    def on_event(self, event: DIEvent) -> None:
        if event.type == DIEventType.REGISTRATION:
            logger.log(self.log_level, f"Registered provider '{event.provider_name}' for token={event.token} (tag={event.tag})")
        elif event.type == DIEventType.RESOLUTION_START:
            logger.log(self.log_level, f"Resolving token={event.token} (tag={event.tag})...")
        elif event.type == DIEventType.RESOLUTION_SUCCESS:
            logger.log(self.log_level, f"✓ Resolved token={event.token} in {event.duration:.4f}s")
        elif event.type == DIEventType.RESOLUTION_FAILURE:
            logger.log(logging.ERROR, f"✗ Failed to resolve token={event.token}: {event.error}")
        elif event.type == DIEventType.LIFECYCLE_STARTUP:
            logger.log(logging.INFO, f"Container startup: {event.metadata.get('app_name', 'unknown')}")

class DIDiagnostics:
    """Coordinator for DI diagnostic listeners."""
    def __init__(self):
        self._listeners: List[DiagnosticListener] = []

    def add_listener(self, listener: DiagnosticListener) -> None:
        """Add a diagnostic listener."""
        self._listeners.append(listener)

    def emit(self, event_type: DIEventType, **kwargs) -> None:
        """Emit a diagnostic event to all listeners."""
        event = DIEvent(type=event_type, **kwargs)
        for listener in self._listeners:
            try:
                listener.on_event(event)
            except Exception as e:
                # Diagnostics should never crash the main application
                logger.error(f"Diagnostic listener error: {e}")

    def measure(self, event_type: DIEventType, **kwargs):
        """Context manager to measure duration of an event."""
        return _DiagnosticMeasure(self, event_type, **kwargs)

class _DiagnosticMeasure:
    def __init__(self, diagnostics: DIDiagnostics, event_type: DIEventType, **kwargs):
        self.diagnostics = diagnostics
        self.event_type = event_type
        self.kwargs = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type:
            self.diagnostics.emit(
                DIEventType.RESOLUTION_FAILURE, 
                duration=duration, 
                error=exc_val,
                **self.kwargs
            )
        else:
            self.diagnostics.emit(
                DIEventType.RESOLUTION_SUCCESS, 
                duration=duration,
                **self.kwargs
            )
