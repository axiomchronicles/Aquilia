"""
Test Template Engine core functionality.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from aquilia.templates import (
    TemplateEngine,
    TemplateLoader,
    InMemoryBytecodeCache,
    SandboxPolicy
)


@pytest.fixture
def temp_templates_dir():
    """Create temporary templates directory."""
    temp_dir = tempfile.mkdtemp()
    templates_path = Path(temp_dir) / "templates"
    templates_path.mkdir()
    
    # Create test templates
    (templates_path / "simple.html").write_text(
        "<h1>Hello {{ name }}!</h1>"
    )
    
    (templates_path / "with_filter.html").write_text(
        "<p>{{ text | upper }}</p>"
    )
    
    (templates_path / "unsafe.html").write_text(
        "<p>{{ unsafe_var }}</p>"
    )
    
    # Module template
    module_path = templates_path / "users"
    module_path.mkdir()
    (module_path / "profile.html").write_text(
        "<h2>{{ user.name }}</h2>"
    )
    
    yield str(templates_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def engine(temp_templates_dir):
    """Create template engine."""
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    cache = InMemoryBytecodeCache()
    
    return TemplateEngine(
        loader=loader,
        bytecode_cache=cache,
        sandbox=True,
        sandbox_policy=SandboxPolicy.strict()
    )


@pytest.mark.asyncio
async def test_simple_render(engine):
    """Test basic template rendering."""
    result = await engine.render("simple.html", {"name": "World"})
    
    assert "<h1>Hello World!</h1>" in result


@pytest.mark.asyncio
async def test_render_with_filter(engine):
    """Test rendering with filters."""
    result = await engine.render("with_filter.html", {"text": "hello"})
    
    assert "<p>HELLO</p>" in result


@pytest.mark.asyncio
async def test_render_sync(engine):
    """Test synchronous rendering."""
    result = engine.render_sync("simple.html", {"name": "Sync"})
    
    assert "<h1>Hello Sync!</h1>" in result


@pytest.mark.asyncio
async def test_render_missing_template(engine):
    """Test rendering non-existent template."""
    from jinja2 import TemplateNotFound
    
    with pytest.raises(TemplateNotFound):
        await engine.render("missing.html", {})


@pytest.mark.asyncio
async def test_render_with_request_ctx(engine):
    """Test rendering with request context."""
    from aquilia.controller.base import RequestCtx
    from aquilia.request import Request
    
    # Create mock request
    request = Request(
        method="GET",
        path="/test",
        headers={},
        query={},
        body=b""
    )
    
    ctx = RequestCtx(request=request)
    
    result = await engine.render("simple.html", {"name": "Ctx"}, request_ctx=ctx)
    
    assert "<h1>Hello Ctx!</h1>" in result


@pytest.mark.asyncio
async def test_template_streaming(engine):
    """Test template streaming."""
    chunks = []
    async for chunk in engine.stream("simple.html", {"name": "Stream"}):
        chunks.append(chunk)
    
    result = b"".join(chunks).decode("utf-8")
    assert "<h1>Hello Stream!</h1>" in result


def test_template_caching(engine):
    """Test template object caching."""
    # First get
    template1 = engine.get_template("simple.html")
    
    # Second get (should use cache)
    template2 = engine.get_template("simple.html")
    
    assert template1 is template2


def test_cache_invalidation(engine):
    """Test cache invalidation."""
    # Get template
    template1 = engine.get_template("simple.html")
    
    # Invalidate
    engine.invalidate_cache("simple.html")
    
    # Get again (should be new instance)
    template2 = engine.get_template("simple.html")
    
    assert template1 is not template2


def test_list_templates(engine):
    """Test listing available templates."""
    templates = engine.list_templates()
    
    assert "simple.html" in templates
    assert "with_filter.html" in templates
    assert "users/profile.html" in templates


def test_register_custom_filter(engine):
    """Test registering custom filter."""
    def reverse_filter(s):
        return s[::-1]
    
    engine.register_filter("reverse", reverse_filter)
    
    # Should be available in environment
    assert "reverse" in engine.env.filters


def test_register_custom_global(engine):
    """Test registering custom global."""
    engine.register_global("APP_NAME", "TestApp")
    
    assert "APP_NAME" in engine.env.globals
    assert engine.env.globals["APP_NAME"] == "TestApp"


@pytest.mark.asyncio
async def test_autoescape(engine):
    """Test HTML autoescaping."""
    result = await engine.render(
        "simple.html",
        {"name": "<script>alert('xss')</script>"}
    )
    
    # Should be escaped
    assert "&lt;script&gt;" in result
    assert "<script>" not in result


@pytest.mark.asyncio
async def test_module_namespaced_template(engine):
    """Test module-namespaced template."""
    result = await engine.render(
        "users/profile.html",
        {"user": {"name": "Alice"}}
    )
    
    assert "<h2>Alice</h2>" in result


def test_sandbox_restricts_unsafe_access(engine):
    """Test sandbox prevents unsafe operations."""
    # Sandboxed environment should not have unsafe globals
    assert "__import__" not in engine.env.globals
    assert "eval" not in engine.env.globals
    assert "open" not in engine.env.globals
