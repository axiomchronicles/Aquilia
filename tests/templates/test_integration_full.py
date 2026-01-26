"""
Integration test: Full template rendering workflow.

Tests the complete flow from template creation through controller rendering.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from aquilia.templates import (
    TemplateEngine,
    TemplateLoader,
    TemplateManager,
    InMemoryBytecodeCache,
    SandboxPolicy
)
from aquilia.controller import Controller, GET
from aquilia.controller.base import RequestCtx
from aquilia.request import Request


@pytest.fixture
def complete_setup():
    """Setup complete template system."""
    temp_dir = tempfile.mkdtemp()
    templates_path = Path(temp_dir) / "templates"
    
    # Create directory structure
    templates_path.mkdir()
    (templates_path / "layouts").mkdir()
    (templates_path / "users").mkdir()
    
    # Create base layout
    (templates_path / "layouts" / "base.html").write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}App{% endblock %}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
    """)
    
    # Create user profile template
    (templates_path / "users" / "profile.html").write_text("""
{% extends "layouts/base.html" %}

{% block title %}{{ user.name }}'s Profile{% endblock %}

{% block content %}
<h1>{{ user.name | e }}</h1>
<p>Email: {{ user.email | e }}</p>
{% if session %}
<p>Logged in as: {{ session.username }}</p>
{% endif %}
{% endblock %}
    """)
    
    # Create loader
    loader = TemplateLoader(search_paths=[str(templates_path)])
    
    # Create engine
    cache = InMemoryBytecodeCache()
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=cache,
        sandbox=True,
        sandbox_policy=SandboxPolicy.strict()
    )
    
    # Create manager
    manager = TemplateManager(engine, loader)
    
    yield {
        "temp_dir": temp_dir,
        "templates_path": templates_path,
        "loader": loader,
        "engine": engine,
        "manager": manager
    }
    
    # Cleanup
    shutil.rmtree(temp_dir)


class UserController(Controller):
    """Test controller with templates."""
    
    prefix = "/users"
    
    def __init__(self, templates):
        self.templates = templates
    
    @GET("/profile/«id:int»")
    async def profile(self, ctx, id: int):
        # Mock user data
        user = {
            "id": id,
            "name": "Alice",
            "email": "alice@example.com"
        }
        return self.render("users/profile.html", {"user": user}, ctx)


@pytest.mark.asyncio
async def test_full_workflow(complete_setup):
    """Test complete workflow: template -> controller -> render."""
    setup = complete_setup
    engine = setup["engine"]
    
    # 1. Compile templates
    manager = setup["manager"]
    result = await manager.compile_all()
    
    assert result["count"] >= 2  # base.html + profile.html
    assert "fingerprint" in result
    
    # 2. Create controller with engine
    controller = UserController(templates=engine)
    
    # 3. Create request context
    request = Request(
        method="GET",
        path="/users/profile/123",
        headers={},
        query={},
        body=b""
    )
    
    ctx = RequestCtx(request=request)
    
    # Add mock session
    ctx.session = type('Session', (), {'username': 'alice'})()
    
    # 4. Render through controller
    response = controller.render(
        "users/profile.html",
        {"user": {"name": "Alice", "email": "alice@example.com"}},
        ctx
    )
    
    # 5. Verify response
    assert response.status == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert callable(response._content)  # Should be async callable
    
    # 6. Execute render and check output
    rendered = await response._content()
    
    assert "Alice" in rendered
    assert "alice@example.com" in rendered
    assert "Logged in as: alice" in rendered
    assert "<title>Alice&#39;s Profile</title>" in rendered or "<title>Alice's Profile</title>" in rendered


@pytest.mark.asyncio
async def test_lint_workflow(complete_setup):
    """Test template linting workflow."""
    setup = complete_setup
    manager = setup["manager"]
    
    # Create template with issues
    templates_path = setup["templates_path"]
    (templates_path / "users" / "bad.html").write_text("""
{{ undefined_var }}
{{ another_undefined }}
    """)
    
    # Lint all templates
    issues = await manager.lint_all(strict_undefined=True)
    
    # Should find undefined variables
    undefined_issues = [i for i in issues if i.code == "undefined-variable"]
    assert len(undefined_issues) >= 2


@pytest.mark.asyncio
async def test_cache_workflow(complete_setup):
    """Test bytecode caching workflow."""
    setup = complete_setup
    engine = setup["engine"]
    
    # First render (cache miss)
    html1 = await engine.render("users/profile.html", {
        "user": {"name": "Bob", "email": "bob@example.com"}
    })
    
    assert "Bob" in html1
    
    # Second render (cache hit)
    html2 = await engine.render("users/profile.html", {
        "user": {"name": "Charlie", "email": "charlie@example.com"}
    })
    
    assert "Charlie" in html2
    
    # Template should be cached
    assert "users/profile.html" in engine._template_cache


@pytest.mark.asyncio
async def test_security_workflow(complete_setup):
    """Test security features workflow."""
    setup = complete_setup
    engine = setup["engine"]
    
    # XSS attempt
    xss_payload = "<script>alert('xss')</script>"
    
    html = await engine.render("users/profile.html", {
        "user": {
            "name": xss_payload,
            "email": "test@example.com"
        }
    })
    
    # Should be escaped
    assert "&lt;script&gt;" in html
    assert "<script>" not in html


@pytest.mark.asyncio
async def test_streaming_workflow(complete_setup):
    """Test streaming rendering workflow."""
    setup = complete_setup
    engine = setup["engine"]
    
    # Stream render
    chunks = []
    async for chunk in engine.stream("users/profile.html", {
        "user": {"name": "Dave", "email": "dave@example.com"}
    }):
        chunks.append(chunk)
    
    # Combine chunks
    html = b"".join(chunks).decode("utf-8")
    
    assert "Dave" in html
    assert "dave@example.com" in html


def test_template_discovery(complete_setup):
    """Test template discovery."""
    setup = complete_setup
    loader = setup["loader"]
    
    templates = loader.list_templates()
    
    assert "layouts/base.html" in templates
    assert "users/profile.html" in templates


@pytest.mark.asyncio
async def test_inspect_workflow(complete_setup):
    """Test template inspection workflow."""
    setup = complete_setup
    manager = setup["manager"]
    
    info = await manager.inspect("users/profile.html")
    
    assert info["name"] == "users/profile.html"
    assert "hash" in info
    assert "size" in info
    assert info["hash"].startswith("sha256:")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
