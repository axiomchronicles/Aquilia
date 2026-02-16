"""
Aquilia Testing - Fault Testing Utilities.

Provides :class:`MockFaultEngine` that captures emitted faults for
assertion, and :class:`CapturedFault` for structured inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from aquilia.faults.core import Fault, FaultDomain, Severity


@dataclass
class CapturedFault:
    """
    A fault captured by :class:`MockFaultEngine`.

    Stores the fault object along with contextual metadata
    for richer assertions.
    """
    fault: Fault
    domain: Optional[str] = None
    app_name: Optional[str] = None
    handler_name: Optional[str] = None
    timestamp: float = 0.0

    @property
    def code(self) -> str:
        return getattr(self.fault, "code", "UNKNOWN")

    @property
    def message(self) -> str:
        return str(self.fault)

    @property
    def severity(self) -> Optional[Severity]:
        return getattr(self.fault, "severity", None)

    def __repr__(self) -> str:
        return (
            f"<CapturedFault code={self.code!r} "
            f"domain={self.domain!r} severity={self.severity}>"
        )


class MockFaultEngine:
    """
    Drop-in replacement for :class:`~aquilia.faults.engine.FaultEngine`
    that captures faults instead of dispatching them.

    Usage::

        engine = MockFaultEngine()
        engine.emit(MyFault("something broke"))

        assert engine.has_fault("MY_FAULT_CODE")
        assert len(engine.captured) == 1
        engine.reset()
    """

    def __init__(self):
        self.captured: List[CapturedFault] = []
        self._handlers: Dict[str, list] = {}

    # ── Emission ───────────────────────────────────────────────────

    def emit(
        self,
        fault: Fault,
        *,
        app_name: Optional[str] = None,
        handler_name: Optional[str] = None,
        **context: Any,
    ):
        """Capture a fault emission."""
        import time
        self.captured.append(CapturedFault(
            fault=fault,
            domain=str(getattr(fault, "domain", "")),
            app_name=app_name,
            handler_name=handler_name,
            timestamp=time.monotonic(),
        ))

    def raise_fault(self, fault: Fault, **kw):
        """Alias used by some subsystems."""
        self.emit(fault, **kw)
        raise fault

    # ── Registration (no-ops for compatibility) ────────────────────

    def register_app(self, app_name: str, handler: Any = None):
        if handler:
            self._handlers.setdefault(app_name, []).append(handler)

    def register_handler(self, domain: str, handler: Any):
        self._handlers.setdefault(domain, []).append(handler)

    # ── Query helpers ──────────────────────────────────────────────

    def has_fault(self, code: str) -> bool:
        """Check if a fault with the given code was captured."""
        return any(c.code == code for c in self.captured)

    def get_faults(
        self,
        code: Optional[str] = None,
        domain: Optional[str] = None,
        severity: Optional[Severity] = None,
    ) -> List[CapturedFault]:
        """Filter captured faults by code, domain, and/or severity."""
        results = self.captured
        if code:
            results = [c for c in results if c.code == code]
        if domain:
            results = [c for c in results if c.domain == domain]
        if severity is not None:
            results = [c for c in results if c.severity == severity]
        return results

    @property
    def fault_codes(self) -> List[str]:
        return [c.code for c in self.captured]

    @property
    def fault_count(self) -> int:
        return len(self.captured)

    @property
    def last_fault(self) -> Optional[CapturedFault]:
        """Return the most recently captured fault, or ``None``."""
        return self.captured[-1] if self.captured else None

    @property
    def last_fault_code(self) -> Optional[str]:
        """Return the code of the most recently captured fault."""
        return self.last_fault.code if self.last_fault else None

    def has_fault_with_severity(self, severity: Severity) -> bool:
        """Check if any fault with given severity was captured."""
        return any(c.severity == severity for c in self.captured)

    # ── Reset ──────────────────────────────────────────────────────

    def reset(self):
        """Clear all captured faults."""
        self.captured.clear()

    # ── Context manager (sync) ─────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.reset()

    # ── Context manager (async) ────────────────────────────────────

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        self.reset()
