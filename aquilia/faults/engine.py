"""
AquilaFaults - Fault Engine.

The FaultEngine is the runtime fault processor that:
1. Captures raw exceptions and converts them to FaultContexts
2. Routes faults through registered handlers
3. Applies fault lifecycle phases (Origin → Annotation → Propagation → Resolution → Emission)
4. Ensures no faults are silently swallowed
5. Emits fault events for observability

The engine is async-safe and cancellation-aware.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Optional, Callable
from contextvars import ContextVar

from .core import (
    Fault,
    FaultContext,
    FaultDomain,
    Severity,
    FaultResult,
    Resolved,
    Transformed,
    Escalate,
)
from .handlers import FaultHandler, ScopedHandlerRegistry
from .domains import FlowCancelledFault, SystemFault


# Context variable for current request/app scope
_current_app: ContextVar[Optional[str]] = ContextVar("current_app", default=None)
_current_route: ContextVar[Optional[str]] = ContextVar("current_route", default=None)
_current_request_id: ContextVar[Optional[str]] = ContextVar("current_request_id", default=None)


class FaultEngine:
    """
    Runtime fault processor.
    
    Responsibilities:
    1. Capture exceptions and convert to FaultContexts
    2. Route faults through handler chain
    3. Apply fault lifecycle phases
    4. Emit fault events
    5. Ensure deterministic fault handling
    
    The engine maintains:
    - Handler registry (scoped handlers)
    - Event listeners (for observability)
    - Fault history (for debugging)
    
    Usage:
        ```python
        engine = FaultEngine()
        
        # Register handlers
        engine.register_global(RetryHandler())
        engine.register_app("auth", SecurityFaultHandler())
        
        # Process fault
        try:
            # ... application code ...
        except Exception as e:
            result = await engine.process(e)
        ```
    """
    
    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        debug: bool = False,
    ):
        """
        Initialize fault engine.
        
        Args:
            logger: Logger for fault events (creates default if None)
            debug: Enable debug mode (verbose logging, history retention)
        """
        self.logger = logger or logging.getLogger("aquilia.faults")
        self.debug = debug
        
        # Handler registry
        self.registry = ScopedHandlerRegistry()
        
        # Event listeners
        self._event_listeners: list[Callable[[FaultContext], None]] = []
        
        # Fault history (debug only)
        self._history: list[FaultContext] = [] if debug else []
        self._max_history = 100
    
    # ========================================================================
    # Handler Registration
    # ========================================================================
    
    def register_global(self, handler: FaultHandler):
        """Register global fault handler."""
        self.registry.register_global(handler)
        self.logger.debug(f"Registered global handler: {handler.__class__.__name__}")
    
    def register_app(self, app: str, handler: FaultHandler):
        """Register app-scoped fault handler."""
        self.registry.register_app(app, handler)
        self.logger.debug(f"Registered app handler for '{app}': {handler.__class__.__name__}")
    
    def register_controller(self, controller: str, handler: FaultHandler):
        """Register controller-scoped fault handler."""
        self.registry.register_controller(controller, handler)
        self.logger.debug(f"Registered controller handler for '{controller}': {handler.__class__.__name__}")
    
    def register_route(self, route: str, handler: FaultHandler):
        """Register route-scoped fault handler."""
        self.registry.register_route(route, handler)
        self.logger.debug(f"Registered route handler for '{route}': {handler.__class__.__name__}")
    
    def on_fault(self, listener: Callable[[FaultContext], None]):
        """
        Register fault event listener.
        
        Listeners are called after fault is captured but before processing.
        Useful for logging, metrics, tracing.
        
        Args:
            listener: Callback receiving FaultContext
        """
        self._event_listeners.append(listener)
    
    # ========================================================================
    # Fault Processing (Core Logic)
    # ========================================================================
    
    async def process(
        self,
        exception: Exception | Fault,
        *,
        app: Optional[str] = None,
        route: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> FaultResult:
        """
        Process exception or fault.
        
        Fault lifecycle phases:
        1. Origin: Exception/Fault created
        2. Annotation: Wrap with FaultContext
        3. Propagation: Route through handlers
        4. Resolution: Resolve, transform, or escalate
        5. Emission: Log and emit event
        
        Args:
            exception: Exception or Fault to process
            app: App name (or use context var)
            route: Route pattern (or use context var)
            request_id: Request ID (or use context var)
        
        Returns:
            FaultResult from handler chain
        """
        # Phase 1: Origin - Convert exception to Fault
        fault = self._to_fault(exception)
        
        # Phase 2: Annotation - Wrap with context
        ctx = self._annotate(
            fault,
            exception if not isinstance(exception, Fault) else None,
            app=app or _current_app.get(),
            route=route or _current_route.get(),
            request_id=request_id or _current_request_id.get(),
        )
        
        # Phase 5: Emission (before processing for observability)
        self._emit(ctx)
        
        # Phase 3 & 4: Propagation & Resolution
        result = await self._propagate(ctx)
        
        # Record in history (debug mode)
        if self.debug:
            self._history.append(ctx)
            if len(self._history) > self._max_history:
                self._history.pop(0)
        
        return result
    
    async def process_async_exception(
        self,
        exception: Exception,
    ) -> FaultResult:
        """
        Process async exception with automatic context capture.
        
        Extracts app/route/request_id from context vars.
        
        Args:
            exception: Exception to process
        
        Returns:
            FaultResult from handler chain
        """
        return await self.process(exception)
    
    # ========================================================================
    # Lifecycle Phase Implementations
    # ========================================================================
    
    def _to_fault(self, exception: Exception | Fault) -> Fault:
        """
        Phase 1: Origin - Convert exception to Fault.
        
        If exception is already a Fault, return as-is.
        Otherwise, wrap in appropriate domain fault.
        
        Args:
            exception: Exception to convert
        
        Returns:
            Fault object
        """
        if isinstance(exception, Fault):
            return exception
        
        # Convert asyncio.CancelledError to FlowCancelledFault
        if isinstance(exception, asyncio.CancelledError):
            return FlowCancelledFault(reason="async cancellation")
        
        # Convert generic exceptions to SystemFault
        return SystemFault(
            code="UNHANDLED_EXCEPTION",
            message=f"Unhandled exception: {type(exception).__name__}: {str(exception)}",
            severity=Severity.ERROR,
            metadata={
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
        )
    
    def _annotate(
        self,
        fault: Fault,
        cause: Optional[Exception],
        *,
        app: Optional[str],
        route: Optional[str],
        request_id: Optional[str],
    ) -> FaultContext:
        """
        Phase 2: Annotation - Wrap fault with runtime context.
        
        Args:
            fault: Fault to annotate
            cause: Original exception (if any)
            app: App name
            route: Route pattern
            request_id: Request ID
        
        Returns:
            FaultContext with runtime metadata
        """
        return FaultContext.capture(
            fault,
            app=app,
            route=route,
            request_id=request_id,
            cause=cause,
        )
    
    async def _propagate(self, ctx: FaultContext) -> FaultResult:
        """
        Phase 3 & 4: Propagation & Resolution - Route through handlers.
        
        Tries handlers in order:
        Route → Controller → App → Global
        
        First handler to return Resolved or Transformed wins.
        If all escalate, returns Escalate.
        
        Args:
            ctx: FaultContext to propagate
        
        Returns:
            FaultResult from handler chain
        """
        # Get applicable handlers
        handlers = self.registry.get_handlers(
            app=ctx.app,
            route=ctx.route,
        )
        
        # Try each handler
        for handler in handlers:
            if not handler.can_handle(ctx):
                continue
            
            try:
                result = await handler.handle(ctx)
                
                # If handler resolved or transformed, stop
                if not isinstance(result, Escalate):
                    self.logger.debug(
                        f"Handler {handler.__class__.__name__} "
                        f"{result.__class__.__name__} fault {ctx.fault.code}"
                    )
                    return result
            
            except Exception as e:
                # Handler itself raised an exception
                self.logger.error(
                    f"Handler {handler.__class__.__name__} raised exception: {e}",
                    exc_info=True,
                )
                # Continue to next handler
        
        # No handler resolved the fault
        self.logger.debug(f"No handler resolved fault {ctx.fault.code}, escalating")
        return Escalate()
    
    def _emit(self, ctx: FaultContext):
        """
        Phase 5: Emission - Log and emit fault event.
        
        Args:
            ctx: FaultContext to emit
        """
        # Log based on severity
        log_level = {
            Severity.INFO: logging.INFO,
            Severity.WARN: logging.WARNING,
            Severity.ERROR: logging.ERROR,
            Severity.FATAL: logging.CRITICAL,
        }[ctx.fault.severity]
        
        self.logger.log(
            log_level,
            f"[{ctx.fault.domain.value.upper()}] {ctx.fault.code}: {ctx.fault.message}",
            extra={
                "fault_context": ctx.to_dict(),
                "trace_id": ctx.trace_id,
                "fingerprint": ctx.fingerprint(),
            },
        )
        
        # Notify listeners
        for listener in self._event_listeners:
            try:
                listener(ctx)
            except Exception as e:
                self.logger.error(f"Fault listener raised exception: {e}")
    
    # ========================================================================
    # Context Management
    # ========================================================================
    
    @staticmethod
    def set_context(
        *,
        app: Optional[str] = None,
        route: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Set fault context for current async task.
        
        Used to automatically capture context when processing faults.
        
        Args:
            app: App name
            route: Route pattern
            request_id: Request ID
        """
        if app is not None:
            _current_app.set(app)
        if route is not None:
            _current_route.set(route)
        if request_id is not None:
            _current_request_id.set(request_id)
    
    @staticmethod
    def clear_context():
        """Clear fault context for current async task."""
        _current_app.set(None)
        _current_route.set(None)
        _current_request_id.set(None)
    
    # ========================================================================
    # Debugging & Inspection
    # ========================================================================
    
    def get_history(self) -> list[FaultContext]:
        """
        Get fault history (debug mode only).
        
        Returns:
            List of recent fault contexts
        """
        return self._history.copy()
    
    def clear_history(self):
        """Clear fault history."""
        self._history.clear()
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get fault engine statistics.
        
        Returns:
            Dictionary with engine stats
        """
        return {
            "handlers": {
                "global": len(self.registry._global),
                "app": len(self.registry._app),
                "controller": len(self.registry._controller),
                "route": len(self.registry._route),
            },
            "listeners": len(self._event_listeners),
            "history_size": len(self._history),
            "debug": self.debug,
        }


# ============================================================================
# Convenience Functions
# ============================================================================

# Global fault engine instance (for convenience)
_default_engine: Optional[FaultEngine] = None


def get_default_engine() -> FaultEngine:
    """
    Get or create default global fault engine.
    
    Returns:
        Global FaultEngine instance
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = FaultEngine()
    return _default_engine


class FaultMiddleware:
    """
    Middleware that bridges the FaultEngine with the request/response lifecycle.
    
    Catches exceptions, processes them through the FaultEngine, and converts
    the result to a Response.
    """
    
    def __init__(self, engine: FaultEngine):
        self.engine = engine
    
    async def __call__(
        self, 
        request: Any, 
        ctx: Any, 
        next_handler: Callable
    ) -> Any:
        try:
            # Set fault context for current task
            self.engine.set_context(
                app=request.state.get("app_name"),
                route=request.state.get("route_pattern"),
                request_id=request.state.get("request_id"),
            )
            
            try:
                return await next_handler(request, ctx)
            except Exception as e:
                # Process fault through engine
                result = await self.engine.process(e)
                
                if isinstance(result, Resolved):
                    # Handler resolved it - convert response
                    from ..response import Response
                    if isinstance(result.response, Response):
                        return result.response
                    
                    # Wrap raw dict/obj in JSON response if status is provided in result or default to 200/500
                    # For now, simplistic conversion:
                    return Response.json(result.response)
                
                # If escalated or transformed, re-raise for ExceptionMiddleware to catch
                raise e
        finally:
            self.engine.clear_context()


async def process_fault(
    exception: Exception | Fault,
    *,
    engine: Optional[FaultEngine] = None,
) -> FaultResult:
    """
    Process fault using engine.
    
    Convenience function for processing faults.
    
    Args:
        exception: Exception or Fault to process
        engine: FaultEngine to use (uses default if None)
    
    Returns:
        FaultResult from handler chain
    """
    eng = engine or get_default_engine()
    return await eng.process(exception)
