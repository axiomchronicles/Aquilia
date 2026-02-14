"""
Test 22: Fault Engine (faults/engine.py)

Tests FaultEngine, FaultHandler, ScopedHandlerRegistry, process_fault.
"""

import pytest
from unittest.mock import MagicMock

from aquilia.faults import (
    FaultEngine,
    FaultHandler,
    FaultContext,
    Fault,
    FaultDomain,
    Severity,
    Resolved,
    Escalate,
    Transformed,
    get_default_engine,
    process_fault,
)
from aquilia.faults.handlers import ScopedHandlerRegistry, CompositeHandler


# ============================================================================
# ScopedHandlerRegistry
# ============================================================================

class TestScopedHandlerRegistry:

    def test_empty(self):
        reg = ScopedHandlerRegistry()
        handlers = reg.get_handlers()
        assert handlers == []

    def test_register_global(self):
        reg = ScopedHandlerRegistry()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        reg.register_global(H())
        handlers = reg.get_handlers()
        assert len(handlers) == 1

    def test_register_app(self):
        reg = ScopedHandlerRegistry()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        reg.register_app("auth", H())
        handlers = reg.get_handlers(app="auth")
        assert len(handlers) == 1
        handlers_other = reg.get_handlers(app="users")
        assert len(handlers_other) == 0

    def test_register_controller(self):
        reg = ScopedHandlerRegistry()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        reg.register_controller("UserCtrl", H())
        handlers = reg.get_handlers(controller="UserCtrl")
        assert len(handlers) == 1

    def test_register_route(self):
        reg = ScopedHandlerRegistry()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        reg.register_route("/users", H())
        handlers = reg.get_handlers(route="/users")
        assert len(handlers) == 1

    def test_resolution_order(self):
        reg = ScopedHandlerRegistry()

        class RouteH(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        class GlobalH(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        reg.register_route("/users", RouteH())
        reg.register_global(GlobalH())
        handlers = reg.get_handlers(route="/users")
        assert len(handlers) == 2
        # Route handler first, then global
        assert isinstance(handlers[0], RouteH)
        assert isinstance(handlers[1], GlobalH)


# ============================================================================
# FaultHandler (abstract)
# ============================================================================

class TestFaultHandler:

    def test_abstract(self):
        with pytest.raises(TypeError):
            FaultHandler()

    def test_subclass(self):
        class MyHandler(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        h = MyHandler()
        assert h.can_handle(MagicMock()) is True  # Default impl


# ============================================================================
# CompositeHandler
# ============================================================================

class TestCompositeHandler:

    @pytest.mark.asyncio
    async def test_first_resolves(self):
        class ResolveH(FaultHandler):
            async def handle(self, ctx):
                return Resolved(response={"ok": True})

        class EscalateH(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        composite = CompositeHandler([ResolveH(), EscalateH()])
        result = await composite.handle(MagicMock())
        assert isinstance(result, Resolved)

    @pytest.mark.asyncio
    async def test_all_escalate(self):
        class EscalateH(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        composite = CompositeHandler([EscalateH(), EscalateH()])
        result = await composite.handle(MagicMock())
        assert isinstance(result, Escalate)


# ============================================================================
# FaultEngine
# ============================================================================

class TestFaultEngine:

    def test_create(self):
        engine = FaultEngine()
        assert engine is not None
        assert engine.debug is False

    def test_debug_mode(self):
        engine = FaultEngine(debug=True)
        assert engine.debug is True

    def test_register_global(self):
        engine = FaultEngine()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        engine.register_global(H())
        stats = engine.get_stats()
        assert stats["handlers"]["global"] == 1

    def test_register_app(self):
        engine = FaultEngine()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        engine.register_app("auth", H())
        stats = engine.get_stats()
        assert stats["handlers"]["app"] == 1

    def test_register_controller(self):
        engine = FaultEngine()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        engine.register_controller("UserCtrl", H())
        stats = engine.get_stats()
        assert stats["handlers"]["controller"] == 1

    def test_register_route(self):
        engine = FaultEngine()

        class H(FaultHandler):
            async def handle(self, ctx):
                return Escalate()

        engine.register_route("/users", H())
        stats = engine.get_stats()
        assert stats["handlers"]["route"] == 1

    def test_on_fault_listener(self):
        engine = FaultEngine()
        engine.on_fault(lambda ctx: None)
        stats = engine.get_stats()
        assert stats["listeners"] == 1

    @pytest.mark.asyncio
    async def test_process_fault(self):
        engine = FaultEngine()
        fault = Fault(code="TEST", message="test", domain=FaultDomain.SYSTEM)
        result = await engine.process(fault)
        # No handlers registered, should escalate
        assert isinstance(result, Escalate)

    @pytest.mark.asyncio
    async def test_process_exception(self):
        engine = FaultEngine()
        result = await engine.process(ValueError("test"))
        assert isinstance(result, Escalate)

    @pytest.mark.asyncio
    async def test_process_with_handler(self):
        engine = FaultEngine()

        class ResolveH(FaultHandler):
            async def handle(self, ctx):
                return Resolved(response={"handled": True})

        engine.register_global(ResolveH())
        fault = Fault(code="ERR", message="err", domain=FaultDomain.IO)
        result = await engine.process(fault)
        assert isinstance(result, Resolved)

    @pytest.mark.asyncio
    async def test_process_debug_history(self):
        engine = FaultEngine(debug=True)
        fault = Fault(code="TEST", message="test", domain=FaultDomain.SYSTEM)
        await engine.process(fault)
        history = engine.get_history()
        assert len(history) == 1

    def test_clear_history(self):
        engine = FaultEngine(debug=True)
        engine.clear_history()
        assert len(engine.get_history()) == 0

    def test_set_clear_context(self):
        FaultEngine.set_context(app="auth", route="/login", request_id="req-1")
        FaultEngine.clear_context()

    @pytest.mark.asyncio
    async def test_on_fault_listener_called(self):
        engine = FaultEngine()
        captured = []

        def listener(ctx):
            captured.append(ctx)

        engine.on_fault(listener)
        fault = Fault(code="X", message="y", domain=FaultDomain.SYSTEM)
        await engine.process(fault)
        assert len(captured) == 1


# ============================================================================
# Convenience functions
# ============================================================================

class TestConvenience:

    def test_get_default_engine(self):
        engine = get_default_engine()
        assert isinstance(engine, FaultEngine)

    @pytest.mark.asyncio
    async def test_process_fault_convenience(self):
        engine = FaultEngine()
        fault = Fault(code="CONV", message="conv", domain=FaultDomain.SYSTEM)
        result = await process_fault(fault, engine=engine)
        assert isinstance(result, Escalate)
