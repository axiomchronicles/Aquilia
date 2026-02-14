"""
Test 21: Templates System (templates/)

Tests TemplateEngine, TemplateLoader, BytecodeCache,
TemplateContext, TemplateSandbox, SandboxPolicy.
"""

import pytest

from aquilia.templates import (
    TemplateEngine,
    TemplateLoader,
    PackageLoader,
    BytecodeCache,
    InMemoryBytecodeCache,
    TemplateMiddleware,
    TemplateContext,
    create_template_context,
    TemplateSandbox,
    SandboxPolicy,
    TemplateManager,
)


# ============================================================================
# TemplateEngine
# ============================================================================

class TestTemplateEngine:

    def test_create(self):
        loader = TemplateLoader(["/tmp/templates"])
        engine = TemplateEngine(loader)
        assert engine is not None

    def test_has_render(self):
        loader = TemplateLoader(["/tmp/templates"])
        engine = TemplateEngine(loader)
        assert hasattr(engine, "render") or hasattr(engine, "render_string")


# ============================================================================
# TemplateLoader
# ============================================================================

class TestTemplateLoader:

    def test_exists(self):
        assert TemplateLoader is not None

    def test_package_loader(self):
        assert PackageLoader is not None


# ============================================================================
# BytecodeCache
# ============================================================================

class TestBytecodeCache:

    def test_base_class(self):
        assert BytecodeCache is not None

    def test_in_memory_cache(self):
        cache = InMemoryBytecodeCache()
        assert isinstance(cache, BytecodeCache)


# ============================================================================
# Template Context
# ============================================================================

class TestTemplateContext:

    def test_exists(self):
        assert TemplateContext is not None

    def test_create_context(self):
        ctx = create_template_context()
        assert ctx is not None


# ============================================================================
# Security
# ============================================================================

class TestTemplateSandbox:

    def test_exists(self):
        assert TemplateSandbox is not None

    def test_sandbox_policy(self):
        assert SandboxPolicy is not None


# ============================================================================
# TemplateMiddleware
# ============================================================================

class TestTemplateMiddleware:

    def test_exists(self):
        assert TemplateMiddleware is not None


# ============================================================================
# TemplateManager
# ============================================================================

class TestTemplateManager:

    def test_exists(self):
        assert TemplateManager is not None
