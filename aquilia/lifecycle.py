"""
Lifecycle Coordinator - Orchestrates startup and shutdown hooks.

This module manages the application lifecycle, ensuring that hooks are called
in the correct order (following dependency graph) with proper error handling
and rollback capabilities.
"""

from typing import Any, Callable, List, Optional, Dict
from dataclasses import dataclass
import asyncio
import inspect
import logging
from enum import Enum


logger = logging.getLogger("aquilia.lifecycle")


class LifecyclePhase(Enum):
    """Lifecycle phases."""
    INIT = "init"
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class LifecycleEvent:
    """Event emitted during lifecycle transitions."""
    phase: LifecyclePhase
    app_name: Optional[str] = None
    message: Optional[str] = None
    error: Optional[Exception] = None


class LifecycleError(Exception):
    """Raised when lifecycle operation fails."""
    pass


class LifecycleCoordinator:
    """
    Coordinates application lifecycle across multiple apps.
    
    Responsibilities:
    - Execute startup hooks in dependency order
    - Execute shutdown hooks in reverse order
    - Handle errors and perform rollback
    - Track lifecycle state
    - Emit lifecycle events
    """
    
    def __init__(self, runtime: Any, config: Any = None):
        """
        Initialize coordinator.
        
        Args:
            runtime: RuntimeRegistry with app_contexts
            config: Optional config for hook parameters
        """
        self.runtime = runtime
        self.config = config
        self.phase = LifecyclePhase.INIT
        self.started_apps: List[str] = []
        self.event_handlers: List[Callable[[LifecycleEvent], None]] = []
        self.logger = logger
    
    def on_event(self, handler: Callable[[LifecycleEvent], None]):
        """
        Register event handler.
        
        Args:
            handler: Callable that receives LifecycleEvent
        """
        self.event_handlers.append(handler)
    
    def _emit_event(self, event: LifecycleEvent):
        """Emit lifecycle event to all handlers."""
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Event handler error: {e}")
    
    async def startup(self):
        """
        Execute startup hooks for all apps in dependency order.
        
        Raises:
            LifecycleError: If any startup hook fails
        """
        if self.phase != LifecyclePhase.INIT:
            raise LifecycleError(
                f"Cannot start from phase {self.phase.value}. Must be in INIT phase."
            )
        
        self.phase = LifecyclePhase.STARTING
        self._emit_event(LifecycleEvent(LifecyclePhase.STARTING))
        
        self.logger.info("Starting application lifecycle...")
        
        try:
            # Apps are already in topological order from registry
            for ctx in self.runtime.meta.app_contexts:
                await self._startup_app(ctx)
            
            self.phase = LifecyclePhase.READY
            self._emit_event(LifecycleEvent(LifecyclePhase.READY))
            self.logger.info(f"✅ All apps started successfully ({len(self.started_apps)} apps)")
        
        except Exception as e:
            self.phase = LifecyclePhase.ERROR
            self._emit_event(LifecycleEvent(
                LifecyclePhase.ERROR,
                message="Startup failed",
                error=e
            ))
            self.logger.error(f"❌ Startup failed: {e}")
            
            # Rollback - shutdown already started apps
            self.logger.info("Rolling back started apps...")
            await self.shutdown()
            
            raise LifecycleError(f"Startup failed: {e}") from e
    
    async def _startup_app(self, ctx: Any):
        """
        Execute startup hook for a single app.
        
        Args:
            ctx: AppContext with on_startup hook
        """
        app_name = ctx.name
        
        if ctx.on_startup is None:
            # No startup hook - skip
            self.started_apps.append(app_name)
            self.logger.debug(f"  ↳ {app_name}: no startup hook")
            return
        
        self.logger.info(f"  ↳ Starting {app_name}...")
        
        try:
            # Get config namespace for this app
            config_ns = ctx.config_namespace or {}
            
            # Get DI container for this app
            di_container = self.runtime.di_containers.get(app_name)
            
            # Start DI container (runs provider startup hooks)
            if di_container and hasattr(di_container, "startup"):
                await di_container.startup()
            
            # Call startup hook
            hook = ctx.on_startup
            if inspect.iscoroutinefunction(hook):
                await hook(config_ns, di_container)
            else:
                hook(config_ns, di_container)
            
            self.started_apps.append(app_name)
            self._emit_event(LifecycleEvent(
                LifecyclePhase.STARTING,
                app_name=app_name,
                message=f"{app_name} started"
            ))
            self.logger.info(f"     ✓ {app_name} started")
        
        except Exception as e:
            self.logger.error(f"     ✗ {app_name} startup failed: {e}")
            raise LifecycleError(f"Startup failed for app '{app_name}': {e}") from e
    
    async def shutdown(self):
        """
        Execute shutdown hooks for all started apps in reverse order.
        
        Does not raise exceptions - logs errors and continues cleanup.
        """
        if self.phase == LifecyclePhase.STOPPED:
            self.logger.debug("Already stopped")
            return
        
        self.phase = LifecyclePhase.STOPPING
        self._emit_event(LifecycleEvent(LifecyclePhase.STOPPING))
        
        self.logger.info("Stopping application...")
        
        # Shutdown in reverse order
        for app_name in reversed(self.started_apps):
            await self._shutdown_app(app_name)
        
        self.phase = LifecyclePhase.STOPPED
        self._emit_event(LifecycleEvent(LifecyclePhase.STOPPED))
        self.logger.info("✅ All apps stopped")
    
    async def _shutdown_app(self, app_name: str):
        """
        Execute shutdown hook for a single app.
        
        Args:
            app_name: Name of app to shutdown
        """
        # Find app context
        ctx = next((c for c in self.runtime.meta.app_contexts if c.name == app_name), None)
        
        if ctx is None or ctx.on_shutdown is None:
            self.logger.debug(f"  ↳ {app_name}: no shutdown hook")
            return
        
        self.logger.info(f"  ↳ Stopping {app_name}...")
        
        try:
            # Get config namespace
            config_ns = ctx.config_namespace or {}
            
            # Get DI container
            di_container = self.runtime.di_containers.get(app_name)
            
            # Call shutdown hook
            hook = ctx.on_shutdown
            if inspect.iscoroutinefunction(hook):
                await hook(config_ns, di_container)
            else:
                hook(config_ns, di_container)
            
            self._emit_event(LifecycleEvent(
                LifecyclePhase.STOPPING,
                app_name=app_name,
                message=f"{app_name} stopped"
            ))
            self.logger.info(f"     ✓ {app_name} stopped")
        
        except Exception as e:
            # Log but don't raise - continue cleanup
            self.logger.error(f"     ✗ {app_name} shutdown error: {e}")
            self._emit_event(LifecycleEvent(
                LifecyclePhase.STOPPING,
                app_name=app_name,
                message=f"{app_name} shutdown error",
                error=e
            ))
    
    async def restart(self):
        """Restart the application (shutdown then startup)."""
        self.logger.info("Restarting application...")
        await self.shutdown()
        self.phase = LifecyclePhase.INIT
        self.started_apps.clear()
        await self.startup()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current lifecycle status.
        
        Returns:
            Status dict with phase and started apps
        """
        return {
            "phase": self.phase.value,
            "started_apps": self.started_apps.copy(),
            "total_apps": len(self.runtime.meta.app_contexts),
        }


class LifecycleManager:
    """
    High-level lifecycle manager with context manager support.
    
    Usage:
        async with LifecycleManager(runtime, config) as manager:
            # Apps are started
            await run_server()
        # Apps automatically shutdown
    """
    
    def __init__(self, runtime: Any, config: Any = None):
        """
        Initialize manager.
        
        Args:
            runtime: RuntimeRegistry
            config: Optional config
        """
        self.coordinator = LifecycleCoordinator(runtime, config)
    
    async def __aenter__(self):
        """Start lifecycle on context entry."""
        await self.coordinator.startup()
        return self.coordinator
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop lifecycle on context exit."""
        await self.coordinator.shutdown()
        return False  # Don't suppress exceptions
    
    def on_event(self, handler: Callable[[LifecycleEvent], None]):
        """Register event handler."""
        self.coordinator.on_event(handler)
        return self


def create_lifecycle_coordinator(runtime: Any, config: Any = None) -> LifecycleCoordinator:
    """
    Factory function to create lifecycle coordinator.
    
    Args:
        runtime: RuntimeRegistry with app_contexts
        config: Optional config
        
    Returns:
        Configured LifecycleCoordinator
    """
    return LifecycleCoordinator(runtime, config)
