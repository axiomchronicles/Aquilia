"""
Test Template Security and Sandboxing.
"""

import pytest
from jinja2 import TemplateSyntaxError
from jinja2.exceptions import SecurityError

from aquilia.templates import (
    TemplateEngine,
    TemplateLoader,
    InMemoryBytecodeCache,
    TemplateSandbox,
    SandboxPolicy
)
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_templates_dir():
    """Create temporary templates directory."""
    temp_dir = tempfile.mkdtemp()
    templates_path = Path(temp_dir) / "templates"
    templates_path.mkdir()
    
    # Safe template
    (templates_path / "safe.html").write_text(
        "<p>{{ text | escape }}</p>"
    )
    
    # Potentially unsafe template
    (templates_path / "unsafe_filter.html").write_text(
        "{{ data | tojson }}"
    )
    
    yield str(templates_path)
    
    shutil.rmtree(temp_dir)


def test_sandbox_policy_strict():
    """Test strict sandbox policy."""
    policy = SandboxPolicy.strict()
    
    assert not policy.allow_unsafe_filters
    assert not policy.allow_unsafe_tests
    assert not policy.allow_unsafe_globals
    assert policy.autoescape


def test_sandbox_policy_permissive():
    """Test permissive sandbox policy."""
    policy = SandboxPolicy.permissive()
    
    assert not policy.allow_unsafe_filters  # Still restrictive
    assert "tojson" in policy.allowed_filters  # But more filters


def test_sandbox_filter_allowlist():
    """Test filter allowlist enforcement."""
    policy = SandboxPolicy.strict()
    
    assert policy.is_filter_allowed("upper")
    assert policy.is_filter_allowed("escape")
    assert not policy.is_filter_allowed("tojson")  # Not in strict policy


def test_sandbox_register_filter():
    """Test registering custom filter."""
    sandbox = TemplateSandbox(policy=SandboxPolicy.strict())
    
    def custom_filter(s):
        return s.upper()
    
    sandbox.register_filter("custom", custom_filter)
    
    assert "custom" in sandbox._custom_filters
    assert sandbox.policy.is_filter_allowed("custom")


def test_sandbox_create_environment():
    """Test creating sandboxed environment."""
    from jinja2.sandbox import SandboxedEnvironment
    
    sandbox = TemplateSandbox(policy=SandboxPolicy.strict())
    env = sandbox.create_environment()
    
    assert isinstance(env, SandboxedEnvironment)
    assert env.autoescape


def test_sandbox_filters_removed():
    """Test disallowed filters are removed."""
    sandbox = TemplateSandbox(policy=SandboxPolicy.strict())
    env = sandbox.create_environment()
    
    # Safe filters should be present
    assert "upper" in env.filters
    assert "escape" in env.filters
    
    # Unsafe filters should be removed
    assert "tojson" not in env.filters


@pytest.mark.asyncio
async def test_sandboxed_engine_safe_rendering(temp_templates_dir):
    """Test sandboxed engine renders safe templates."""
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    engine = TemplateEngine(
        loader=loader,
        sandbox=True,
        sandbox_policy=SandboxPolicy.strict()
    )
    
    result = await engine.render("safe.html", {"text": "<script>xss</script>"})
    
    # Should be escaped
    assert "&lt;script&gt;" in result


@pytest.mark.asyncio
async def test_sandboxed_engine_blocks_unsafe_filter(temp_templates_dir):
    """Test sandboxed engine blocks unsafe filters."""
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    engine = TemplateEngine(
        loader=loader,
        sandbox=True,
        sandbox_policy=SandboxPolicy.strict()
    )
    
    # tojson filter not in strict policy, template should fail
    with pytest.raises(Exception):  # Will raise UndefinedError or similar
        await engine.render("unsafe_filter.html", {"data": {"key": "value"}})


def test_custom_safe_filters():
    """Test custom safe filters are registered."""
    from aquilia.templates.security import create_safe_filters
    
    filters = create_safe_filters()
    
    assert "format_date" in filters
    assert "format_currency" in filters
    assert "pluralize" in filters
    assert "sanitize_html" in filters
    assert callable(filters["format_date"])


def test_format_date_filter():
    """Test format_date filter."""
    from aquilia.templates.security import create_safe_filters
    from datetime import datetime
    
    filters = create_safe_filters()
    format_date = filters["format_date"]
    
    dt = datetime(2026, 1, 26, 12, 30)
    result = format_date(dt, "%Y-%m-%d")
    
    assert result == "2026-01-26"


def test_format_currency_filter():
    """Test format_currency filter."""
    from aquilia.templates.security import create_safe_filters
    
    filters = create_safe_filters()
    format_currency = filters["format_currency"]
    
    assert format_currency(1234.56, "USD") == "$1,234.56"
    assert format_currency(9999.99, "EUR") == "€9,999.99"
    assert format_currency(500, "GBP") == "£500.00"


def test_pluralize_filter():
    """Test pluralize filter."""
    from aquilia.templates.security import create_safe_filters
    
    filters = create_safe_filters()
    pluralize = filters["pluralize"]
    
    assert pluralize(1) == ""
    assert pluralize(0) == "s"
    assert pluralize(2) == "s"
    assert pluralize(1, "", "es") == ""
    assert pluralize(2, "", "es") == "es"


def test_sanitize_html_filter():
    """Test sanitize_html filter."""
    from aquilia.templates.security import create_safe_filters
    
    filters = create_safe_filters()
    sanitize = filters["sanitize_html"]
    
    # Should remove script tags
    result = sanitize("<p>Hello</p><script>alert('xss')</script>")
    assert "<script>" not in result
    assert "<p>Hello</p>" in result
    
    # Should remove event handlers
    result = sanitize('<a href="#" onclick="alert()">Link</a>')
    assert "onclick" not in result


def test_safe_globals():
    """Test safe global functions."""
    from aquilia.templates.security import create_safe_globals
    
    globals_dict = create_safe_globals()
    
    assert "url_for" in globals_dict
    assert "static_url" in globals_dict
    assert "csrf_token" in globals_dict
    assert "config" in globals_dict
    assert callable(globals_dict["url_for"])


def test_autoescape_html():
    """Test HTML autoescaping."""
    sandbox = TemplateSandbox(policy=SandboxPolicy.strict())
    env = sandbox.create_environment()
    
    template = env.from_string("<p>{{ text }}</p>")
    result = template.render(text="<script>alert('xss')</script>")
    
    assert "&lt;script&gt;" in result
    assert "<script>" not in result


def test_sandbox_immutable_option():
    """Test immutable sandbox environment."""
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    
    sandbox = TemplateSandbox(policy=SandboxPolicy.strict(), immutable=True)
    env = sandbox.create_environment()
    
    assert isinstance(env, ImmutableSandboxedEnvironment)


@pytest.mark.asyncio
async def test_xss_protection(temp_templates_dir):
    """Test XSS protection in templates."""
    loader = TemplateLoader(search_paths=[temp_templates_dir])
    engine = TemplateEngine(
        loader=loader,
        sandbox=True,
        autoescape=True
    )
    
    # Create template with user input
    xss_payload = "<img src=x onerror=alert('xss')>"
    
    result = await engine.render("safe.html", {"text": xss_payload})
    
    # Should be escaped
    assert "&lt;img" in result
    assert "onerror=" not in result or "onerror=alert" not in result
