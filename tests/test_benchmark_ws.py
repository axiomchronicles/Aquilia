"""
Tests for the benchmark WebSocket controller.
Verifies:
  1. @Socket decorator attaches correct metadata
  2. @OnConnect / @OnDisconnect / @Event decorators attach handler metadata
  3. The Event handler name matches what ws_bench.py will send
"""
import pytest
import inspect


def test_socket_metadata():
    from benchmark.apps.aquilia_app.ws_controller import BenchSocketController

    assert hasattr(BenchSocketController, "__socket_metadata__"), (
        "Missing @Socket() decorator – __socket_metadata__ not set"
    )
    meta = BenchSocketController.__socket_metadata__
    assert meta["path"] == "/ws"


def test_handlers_registered():
    from benchmark.apps.aquilia_app.ws_controller import BenchSocketController

    handlers = {}
    for name, method in inspect.getmembers(BenchSocketController, inspect.isfunction):
        if hasattr(method, "__socket_handler__"):
            h = method.__socket_handler__
            handlers[h.get("type", h.get("event", name))] = h

    assert "on_connect" in handlers, "Missing @OnConnect() handler"
    assert "on_disconnect" in handlers, "Missing @OnDisconnect() handler"

    # The echo event handler
    event_handlers = {
        h["event"]: h
        for h in handlers.values()
        if h.get("type") == "event"
    }
    assert "echo" in event_handlers, (
        f"Missing @Event('echo') handler.  Found events: {list(event_handlers.keys())}"
    )


def test_controller_inherits_socket_controller():
    from benchmark.apps.aquilia_app.ws_controller import BenchSocketController
    from aquilia.sockets import SocketController

    assert issubclass(BenchSocketController, SocketController)


def test_compiler_accepts_controller():
    """The SocketCompiler should be able to compile our controller."""
    from benchmark.apps.aquilia_app.ws_controller import BenchSocketController
    from aquilia.sockets.compile import SocketCompiler

    compiler = SocketCompiler()
    metadata = compiler.compile_controller(BenchSocketController)

    assert metadata.path_pattern == "/ws"
    assert metadata.class_name == "BenchSocketController"

    event_names = [e.event for e in metadata.events]
    assert "echo" in event_names, f"Expected 'echo' event, got {event_names}"
