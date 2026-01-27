"""
Comprehensive Integration Tests for Enhanced Request & Response

Tests all new integration features:
- Identity/Auth integration
- Session integration
- DI Container integration
- Template context
- Lifecycle hooks
- Fault handling
- Metrics & tracing
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Any, Dict

from aquilia.request import Request
from aquilia.response import Response
from aquilia.faults import Fault, FaultDomain, Severity


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_identity():
    """Mock Identity object."""
    identity = Mock()
    identity.id = "user_123"
    identity.has_role = Mock(side_effect=lambda role: role == "admin")
    identity.has_scope = Mock(side_effect=lambda scope: scope in ["read", "write"])
    return identity


@pytest.fixture
def mock_session():
    """Mock Session object."""
    session = Mock()
    session.id = "session_abc"
    session.is_authenticated = True
    return session


@pytest.fixture
def mock_container():
    """Mock DI Container."""
    container = Mock()
    
    async def mock_resolve_async(service_type, optional=False):
        # Return mock instances for known types
        if optional:
            return None
        return Mock()
    
    container.resolve_async = AsyncMock(side_effect=mock_resolve_async)
    container.resolve = Mock(return_value=Mock())
    return container


@pytest.fixture
def basic_scope():
    """Basic ASGI scope."""
    return {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"foo=bar",
        "headers": [
            (b"host", b"example.com"),
            (b"user-agent", b"Test/1.0"),
        ],
    }


@pytest.fixture
async def mock_receive():
    """Mock ASGI receive callable."""
    async def _receive():
        return {"type": "http.disconnect"}
    return _receive


@pytest.fixture
def request_with_auth(basic_scope, mock_receive, mock_identity, mock_session, mock_container):
    """Request with full auth/session/DI setup."""
    request = Request(basic_scope, mock_receive)
    request.state["identity"] = mock_identity
    request.state["session"] = mock_session
    request.state["di_container"] = mock_container
    request.state["request_id"] = "req_123"
    request.state["trace_id"] = "trace_456"
    return request


# ============================================================================
# Identity Integration Tests
# ============================================================================

def test_request_identity_property(request_with_auth, mock_identity):
    """Test identity property returns correct identity."""
    assert request_with_auth.identity == mock_identity
    assert request_with_auth.identity.id == "user_123"


def test_request_authenticated_property(request_with_auth, basic_scope, mock_receive):
    """Test authenticated property."""
    # With identity
    assert request_with_auth.authenticated is True
    
    # Without identity
    request_no_auth = Request(basic_scope, mock_receive)
    assert request_no_auth.authenticated is False


def test_request_require_identity_success(request_with_auth, mock_identity):
    """Test require_identity returns identity when present."""
    identity = request_with_auth.require_identity()
    assert identity == mock_identity


def test_request_require_identity_raises(basic_scope, mock_receive):
    """Test require_identity raises fault when missing."""
    request = Request(basic_scope, mock_receive)
    
    with pytest.raises(Fault) as exc_info:
        request.require_identity()
    
    fault = exc_info.value
    assert fault.code == "AUTH_REQUIRED"
    assert fault.domain == FaultDomain.SECURITY


def test_request_has_role(request_with_auth):
    """Test has_role method."""
    assert request_with_auth.has_role("admin") is True
    assert request_with_auth.has_role("user") is False


def test_request_has_scope(request_with_auth):
    """Test has_scope method."""
    assert request_with_auth.has_scope("read") is True
    assert request_with_auth.has_scope("write") is True
    assert request_with_auth.has_scope("delete") is False


# ============================================================================
# Session Integration Tests
# ============================================================================

def test_request_session_property(request_with_auth, mock_session):
    """Test session property returns correct session."""
    assert request_with_auth.session == mock_session
    assert request_with_auth.session.id == "session_abc"


def test_request_require_session_success(request_with_auth, mock_session):
    """Test require_session returns session when present."""
    session = request_with_auth.require_session()
    assert session == mock_session


def test_request_require_session_raises(basic_scope, mock_receive):
    """Test require_session raises fault when missing."""
    request = Request(basic_scope, mock_receive)
    
    with pytest.raises(Fault) as exc_info:
        request.require_session()
    
    fault = exc_info.value
    assert fault.code == "SESSION_REQUIRED"


def test_request_session_id(request_with_auth):
    """Test session_id property."""
    assert request_with_auth.session_id == "session_abc"


def test_request_session_id_none_when_no_session(basic_scope, mock_receive):
    """Test session_id returns None when no session."""
    request = Request(basic_scope, mock_receive)
    assert request.session_id is None


# ============================================================================
# DI Container Integration Tests
# ============================================================================

def test_request_container_property(request_with_auth, mock_container):
    """Test container property returns correct container."""
    assert request_with_auth.container == mock_container


@pytest.mark.asyncio
async def test_request_resolve(request_with_auth, mock_container):
    """Test resolve method."""
    service = await request_with_auth.resolve(Mock, optional=True)
    assert service is None  # Mock returns None for optional
    
    mock_container.resolve_async.assert_called_once()


@pytest.mark.asyncio
async def test_request_resolve_raises_when_no_container(basic_scope, mock_receive):
    """Test resolve raises when container missing."""
    request = Request(basic_scope, mock_receive)
    
    with pytest.raises(RuntimeError, match="DI container not available"):
        await request.resolve(Mock)


@pytest.mark.asyncio
async def test_request_inject(request_with_auth):
    """Test inject method for multiple services."""
    services = await request_with_auth.inject(
        auth=Mock,
        session=Mock,
    )
    
    assert "auth" in services
    assert "session" in services


# ============================================================================
# Template Context Integration Tests
# ============================================================================

def test_request_template_context(request_with_auth):
    """Test template_context property includes all auto-injected vars."""
    context = request_with_auth.template_context
    
    assert "request" in context
    assert "identity" in context
    assert "session" in context
    assert "authenticated" in context
    assert "url" in context
    assert "method" in context
    assert "path" in context
    assert context["authenticated"] is True
    assert context["method"] == "GET"
    assert context["path"] == "/test"


def test_request_add_template_context(request_with_auth):
    """Test add_template_context method."""
    request_with_auth.add_template_context(title="Home", user="John")
    
    context = request_with_auth.template_context
    assert context["title"] == "Home"
    assert context["user"] == "John"


# ============================================================================
# Lifecycle Hooks Tests
# ============================================================================

@pytest.mark.asyncio
async def test_request_emit_effect(request_with_auth):
    """Test emit_effect method."""
    mock_lifecycle = Mock()
    mock_lifecycle.emit = AsyncMock()
    request_with_auth.state["lifecycle_manager"] = mock_lifecycle
    
    await request_with_auth.emit_effect("user.login", user_id="123")
    
    mock_lifecycle.emit.assert_called_once_with(
        "user.login",
        request=request_with_auth,
        user_id="123"
    )


@pytest.mark.asyncio
async def test_request_before_response_callback(request_with_auth):
    """Test before_response callback registration."""
    callback = AsyncMock()
    await request_with_auth.before_response(callback)
    
    assert callback in request_with_auth.state["before_response_callbacks"]


@pytest.mark.asyncio
async def test_request_after_response_callback(request_with_auth):
    """Test after_response callback registration."""
    callback = AsyncMock()
    await request_with_auth.after_response(callback)
    
    assert callback in request_with_auth.state["after_response_callbacks"]


# ============================================================================
# Fault Handling Tests
# ============================================================================

def test_request_fault_context(request_with_auth):
    """Test fault_context includes request metadata."""
    context = request_with_auth.fault_context()
    
    assert context["method"] == "GET"
    assert context["path"] == "/test"
    assert context["identity_id"] == "user_123"
    assert context["session_id"] == "session_abc"
    assert context["request_id"] == "req_123"
    assert context["trace_id"] == "trace_456"
    assert context["authenticated"] is True


@pytest.mark.asyncio
async def test_request_report_fault(request_with_auth):
    """Test report_fault method."""
    mock_fault_engine = Mock()
    mock_fault_engine.process = AsyncMock()
    request_with_auth.state["fault_engine"] = mock_fault_engine
    
    fault = Fault(
        code="TEST_FAULT",
        message="Test fault",
        domain=FaultDomain.SYSTEM,
        severity=Severity.ERROR,
    )
    
    await request_with_auth.report_fault(fault)
    
    mock_fault_engine.process.assert_called_once_with(fault)
    # Check fault was enriched with context
    assert "method" in fault.metadata
    assert "identity_id" in fault.metadata


# ============================================================================
# Metrics & Tracing Tests
# ============================================================================

def test_request_trace_id(request_with_auth):
    """Test trace_id property."""
    assert request_with_auth.trace_id == "trace_456"


def test_request_id_property(request_with_auth):
    """Test request_id property."""
    assert request_with_auth.request_id == "req_123"


def test_request_record_metric(request_with_auth):
    """Test record_metric method."""
    mock_metrics = Mock()
    mock_metrics.record = Mock()
    request_with_auth.state["metrics_collector"] = mock_metrics
    
    request_with_auth.record_metric("test.metric", 123.45, tag1="value1")
    
    mock_metrics.record.assert_called_once()
    call_args = mock_metrics.record.call_args
    assert call_args[0][0] == "test.metric"
    assert call_args[0][1] == 123.45
    assert call_args[1]["tag1"] == "value1"
    assert call_args[1]["method"] == "GET"
    assert call_args[1]["authenticated"] is True


# ============================================================================
# Response Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_response_render_with_request():
    """Test Response.render with request for auto-injection."""
    # Setup mock request
    request = Mock()
    request.template_context = {
        "request": request,
        "identity": Mock(id="user_123"),
        "authenticated": True,
    }
    
    # Mock template engine
    mock_engine = Mock()
    mock_engine.render = AsyncMock(return_value="<html>Hello</html>")
    request.state = {"template_engine": mock_engine}
    request.resolve = AsyncMock(return_value=mock_engine)
    
    # Render
    response = await Response.render(
        "test.html",
        {"title": "Test"},
        request=request,
    )
    
    assert response.status == 200
    mock_engine.render.assert_called_once()
    
    # Check context was merged
    call_args = mock_engine.render.call_args[0]
    context = call_args[1]
    assert "title" in context
    assert "identity" in context
    assert "authenticated" in context


@pytest.mark.asyncio
async def test_response_commit_session():
    """Test response commit_session method."""
    # Setup mocks
    request = Mock()
    mock_session = Mock()
    request.session = mock_session
    request.state = {}
    
    mock_session_engine = Mock()
    mock_session_engine.commit = AsyncMock()
    
    async def mock_resolve(service_type, optional=False):
        from aquilia.sessions.engine import SessionEngine
        if service_type == SessionEngine:
            return mock_session_engine
        return None
    
    request.resolve = mock_resolve
    
    response = Response.json({"status": "ok"})
    await response.commit_session(request)
    
    mock_session_engine.commit.assert_called_once_with(mock_session, response)


@pytest.mark.asyncio
async def test_response_execute_before_send_hooks():
    """Test execute_before_send_hooks method."""
    callback = AsyncMock()
    
    request = Mock()
    request.state = {"before_response_callbacks": [callback]}
    
    response = Response.json({"status": "ok"})
    await response.execute_before_send_hooks(request)
    
    callback.assert_called_once_with(response)


@pytest.mark.asyncio
async def test_response_execute_after_send_hooks():
    """Test execute_after_send_hooks method."""
    callback = AsyncMock()
    
    request = Mock()
    request.state = {"after_response_callbacks": [callback]}
    
    response = Response.json({"status": "ok"})
    await response.execute_after_send_hooks(request)
    
    callback.assert_called_once_with(response)


def test_response_record_response_metrics():
    """Test record_response_metrics method."""
    request = Mock()
    request.record_metric = Mock()
    
    response = Response.json({"status": "ok"})
    response.record_response_metrics(request, 123.45)
    
    assert request.record_metric.call_count == 2  # time and size


def test_response_from_fault():
    """Test Response.from_fault creates appropriate response."""
    fault = Fault(
        code="AUTH_REQUIRED",
        message="Authentication required",
        domain=FaultDomain.SECURITY,
        severity=Severity.WARN,
    )
    
    response = Response.from_fault(fault)
    
    assert response.status == 401
    # Content will be JSON


# ============================================================================
# Integration Test: Full Request-Response Cycle
# ============================================================================

@pytest.mark.asyncio
async def test_full_request_response_cycle(
    basic_scope,
    mock_receive,
    mock_identity,
    mock_session,
    mock_container
):
    """Test complete request-response cycle with all integrations."""
    # Setup request
    request = Request(basic_scope, mock_receive)
    request.state["identity"] = mock_identity
    request.state["session"] = mock_session
    request.state["di_container"] = mock_container
    request.state["request_id"] = "req_test"
    
    # Add template context
    request.add_template_context(page="Home")
    
    # Register callbacks
    before_called = []
    after_called = []
    
    async def before_hook(response):
        before_called.append(True)
    
    async def after_hook(response):
        after_called.append(True)
    
    await request.before_response(before_hook)
    await request.after_response(after_hook)
    
    # Create response
    response = Response.json({"status": "ok"})
    
    # Execute hooks
    await response.execute_before_send_hooks(request)
    await response.execute_after_send_hooks(request)
    
    # Verify
    assert request.authenticated is True
    assert request.identity == mock_identity
    assert request.session == mock_session
    assert "page" in request.template_context
    assert len(before_called) == 1
    assert len(after_called) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
