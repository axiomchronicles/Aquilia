"""
Lifecycle management for providers and containers.
"""

from typing import Any, Callable, Coroutine, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class DisposalStrategy(str, Enum):
    """Strategy for disposing instances."""
    
    LIFO = "lifo"  # Last in, first out (default)
    FIFO = "fifo"  # First in, first out
    PARALLEL = "parallel"  # All in parallel


@dataclass
class LifecycleHook:
    """
    Lifecycle hook registration.
    
    Hooks are called during container startup/shutdown.
    """
    
    name: str
    callback: Callable[[], Coroutine[Any, Any, None]]
    priority: int = 0  # Higher priority runs first
    phase: str = "shutdown"  # "startup" or "shutdown"


class Lifecycle:
    """
    Manages lifecycle hooks and deterministic disposal.
    
    Ensures proper cleanup order and error handling.
    """
    
    __slots__ = (
        "_startup_hooks",
        "_shutdown_hooks",
        "_finalizers",
        "_disposal_strategy",
    )
    
    def __init__(self, disposal_strategy: DisposalStrategy = DisposalStrategy.LIFO):
        self._startup_hooks: List[LifecycleHook] = []
        self._shutdown_hooks: List[LifecycleHook] = []
        self._finalizers: List[Callable[[], Coroutine]] = []
        self._disposal_strategy = disposal_strategy
    
    def on_startup(
        self,
        callback: Callable[[], Coroutine],
        *,
        name: str = "startup_hook",
        priority: int = 0,
    ) -> None:
        """
        Register startup hook.
        
        Args:
            callback: Async callback to run on startup
            name: Hook name for diagnostics
            priority: Higher priority runs first
        """
        hook = LifecycleHook(
            name=name,
            callback=callback,
            priority=priority,
            phase="startup",
        )
        self._startup_hooks.append(hook)
        self._startup_hooks.sort(key=lambda h: -h.priority)  # Descending
    
    def on_shutdown(
        self,
        callback: Callable[[], Coroutine],
        *,
        name: str = "shutdown_hook",
        priority: int = 0,
    ) -> None:
        """
        Register shutdown hook.
        
        Args:
            callback: Async callback to run on shutdown
            name: Hook name for diagnostics
            priority: Higher priority runs first
        """
        hook = LifecycleHook(
            name=name,
            callback=callback,
            priority=priority,
            phase="shutdown",
        )
        self._shutdown_hooks.append(hook)
        self._shutdown_hooks.sort(key=lambda h: -h.priority)  # Descending
    
    def register_finalizer(
        self,
        finalizer: Callable[[], Coroutine],
    ) -> None:
        """
        Register finalizer for cleanup.
        
        Finalizers are called in reverse order (LIFO) during shutdown.
        
        Args:
            finalizer: Async callback for cleanup
        """
        self._finalizers.append(finalizer)
    
    async def run_startup_hooks(self) -> None:
        """Run all startup hooks in priority order."""
        errors = []
        
        for hook in self._startup_hooks:
            try:
                await hook.callback()
            except Exception as e:
                errors.append((hook.name, e))
        
        if errors:
            error_msg = "Startup hooks failed:\n"
            for name, error in errors:
                error_msg += f"  - {name}: {error}\n"
            raise RuntimeError(error_msg)
    
    async def run_shutdown_hooks(self) -> None:
        """Run all shutdown hooks in priority order."""
        errors = []
        
        for hook in self._shutdown_hooks:
            try:
                await hook.callback()
            except Exception as e:
                errors.append((hook.name, e))
                # Continue with other hooks even if one fails
        
        if errors:
            # Log but don't raise during shutdown
            for name, error in errors:
                print(f"Warning: Shutdown hook '{name}' failed: {error}")
    
    async def run_finalizers(self) -> None:
        """Run all finalizers according to disposal strategy."""
        if self._disposal_strategy == DisposalStrategy.LIFO:
            await self._run_finalizers_lifo()
        elif self._disposal_strategy == DisposalStrategy.FIFO:
            await self._run_finalizers_fifo()
        elif self._disposal_strategy == DisposalStrategy.PARALLEL:
            await self._run_finalizers_parallel()
    
    async def _run_finalizers_lifo(self) -> None:
        """Run finalizers in LIFO order."""
        errors = []
        
        for finalizer in reversed(self._finalizers):
            try:
                await finalizer()
            except Exception as e:
                errors.append(e)
                # Continue with remaining finalizers
        
        if errors:
            # Log but don't raise
            for error in errors:
                print(f"Warning: Finalizer failed: {error}")
    
    async def _run_finalizers_fifo(self) -> None:
        """Run finalizers in FIFO order."""
        errors = []
        
        for finalizer in self._finalizers:
            try:
                await finalizer()
            except Exception as e:
                errors.append(e)
        
        if errors:
            for error in errors:
                print(f"Warning: Finalizer failed: {error}")
    
    async def _run_finalizers_parallel(self) -> None:
        """Run all finalizers in parallel."""
        tasks = [finalizer() for finalizer in self._finalizers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            for error in errors:
                print(f"Warning: Finalizer failed: {error}")
    
    def clear(self) -> None:
        """Clear all hooks and finalizers."""
        self._startup_hooks.clear()
        self._shutdown_hooks.clear()
        self._finalizers.clear()


# Context manager support for lifecycle
class LifecycleContext:
    """Context manager for automatic lifecycle management."""
    
    def __init__(self, lifecycle: Lifecycle):
        self.lifecycle = lifecycle
    
    async def __aenter__(self):
        await self.lifecycle.run_startup_hooks()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.lifecycle.run_shutdown_hooks()
        await self.lifecycle.run_finalizers()
        return False
