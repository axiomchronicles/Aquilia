"""
Test Controller integration with templates.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from aquilia.templates import TemplateEngine, TemplateLoader, InMemoryBytecodeCache
from aquilia.controller import Controller, RequestCtx
from aquilia.request import Request
from aquilia.response import Response


@pytest.fixture
def temp_templates_dir():
    """Create temporary templates directory."""
    temp_dir = tempfile.mkdtemp()
    templates_path = Path(temp_dir) / "templates"
    templates_path.mkdir()
    
    (templates_path / "profile.html").write_text(
        "<h1>{{ user.name }}</h1><p>{{ user.email }}</p>"
    )
    
    (templates_path / "list.html").write_text(
        "<ul>{% for item in items %}<li>{{ item }}</li>{% endfor %}</ul>"
    )
    
    yield str(templates_path)
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def engine(temp_templates_dir):
    """Create template engine."""
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    cache = InMemoryBytecodeCache()
    
    return TemplateEngine(loader=loader, bytecode_cache=cache, sandbox=True)


class TemplateTestController(Controller):
    """Test controller with template rendering."""
    
    prefix = "/test"
    
    def __init__(self, templates: TemplateEngine):
        self.templates = templates


def test_controller_render_method(engine):
    """Test controller render helper method."""
    controller = TemplateTestController(templates=engine)
    
    # Create request context
    request = Request(
        method="GET",
        path="/test/profile",
        headers={},
        query={},
        body=b""
    )
    ctx = RequestCtx(request=request)
    
    # Render template
    response = controller.render(
        "profile.html",
        {"user": {"name": "Alice", "email": "alice@example.com"}},
        ctx
    )
    
    assert isinstance(response, Response)
    assert response.status == 200


def test_controller_render_without_engine():
    """Test controller render fails without engine."""
    controller = Controller()
    
    request = Request(
        method="GET",
        path="/test",
        headers={},
        query={},
        body=b""
    )
    ctx = RequestCtx(request=request)
    
    with pytest.raises(RuntimeError, match="Template engine not available"):
        controller.render("test.html", {}, ctx)


def test_controller_render_with_status(engine):
    """Test controller render with custom status."""
    controller = TemplateTestController(templates=engine)
    
    request = Request(
        method="GET",
        path="/test",
        headers={},
        query={},
        body=b""
    )
    ctx = RequestCtx(request=request)
    
    response = controller.render(
        "profile.html",
        {"user": {"name": "Bob", "email": "bob@example.com"}},
        ctx,
        status=201
    )
    
    assert response.status == 201


def test_controller_render_with_headers(engine):
    """Test controller render with custom headers."""
    controller = TemplateTestController(templates=engine)
    
    request = Request(
        method="GET",
        path="/test",
        headers={},
        query={},
        body=b""
    )
    ctx = RequestCtx(request=request)
    
    response = controller.render(
        "profile.html",
        {"user": {"name": "Charlie", "email": "charlie@example.com"}},
        ctx,
        headers={"X-Custom": "value"}
    )
    
    assert "X-Custom" in response.headers
    assert response.headers["X-Custom"] == "value"


@pytest.mark.asyncio
async def test_controller_render_integration(engine):
    """Test full controller rendering integration."""
    controller = TemplateTestController(templates=engine)
    
    # Create request context with session and identity
    from aquilia.sessions import Session
    from aquilia.auth.core import Identity
    
    request = Request(
        method="GET",
        path="/test/profile",
        headers={},
        query={},
        body=b""
    )
    
    # Mock identity
    identity = type('Identity', (), {
        'id': '123',
        'username': 'alice',
        'roles': ['user']
    })()
    
    ctx = RequestCtx(
        request=request,
        identity=identity
    )
    
    response = controller.render(
        "profile.html",
        {"user": {"name": "Alice", "email": "alice@example.com"}},
        ctx
    )
    
    # Response should have async content
    assert hasattr(response._content, '__call__')


def test_response_render_classmethod(engine):
    """Test Response.render class method."""
    response = Response.render(
        "profile.html",
        {"user": {"name": "Dave", "email": "dave@example.com"}},
        engine=engine
    )
    
    assert isinstance(response, Response)
    assert response.status == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_response_render_without_engine():
    """Test Response.render fails without engine."""
    with pytest.raises(ValueError, match="TemplateEngine not provided"):
        Response.render("test.html", {})


def test_response_render_with_status():
    """Test Response.render with custom status."""
    from aquilia.templates import TemplateEngine, TemplateLoader
    
    loader = TemplateLoader(search_paths=[])
    engine = TemplateEngine(loader=loader)
    
    response = Response.render(
        "test.html",
        {},
        status=404,
        engine=engine
    )
    
    assert response.status == 404


def test_controller_template_attribute(engine):
    """Test controller can access templates attribute."""
    controller = TemplateTestController(templates=engine)
    
    assert hasattr(controller, "templates")
    assert controller.templates is engine


def test_controller_render_list_template(engine):
    """Test rendering template with list data."""
    controller = TemplateTestController(templates=engine)
    
    request = Request(
        method="GET",
        path="/test/list",
        headers={},
        query={},
        body=b""
    )
    ctx = RequestCtx(request=request)
    
    response = controller.render(
        "list.html",
        {"items": ["Apple", "Banana", "Cherry"]},
        ctx
    )
    
    assert isinstance(response, Response)
