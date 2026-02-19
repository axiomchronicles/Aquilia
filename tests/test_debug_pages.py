"""
Tests for Aquilia Debug Pages — exception pages, HTTP error pages, welcome page.

Tests cover:
- Debug exception page rendering (dark/light mode, traceback, source, locals)
- HTTP error pages for each status code
- Welcome/starter page
- ExceptionMiddleware HTML rendering integration
- ASGIAdapter debug 404 page
- DebugPageRenderer class
- CLI generator starter page creation
"""

import pytest
import traceback
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Debug page rendering tests
# ---------------------------------------------------------------------------

from aquilia.debug.pages import (
    render_debug_exception_page,
    render_http_error_page,
    render_welcome_page,
    DebugPageRenderer,
    _esc,
    _read_source_lines,
    _extract_frames,
    _extract_request_info,
    _format_code_block,
    _format_locals_section,
    _syntax_highlight_line,
)


class TestEscapeFunction:
    """Test HTML escaping helper."""

    def test_escapes_angle_brackets(self):
        assert "&lt;" in _esc("<script>")
        assert "&gt;" in _esc("</script>")

    def test_escapes_ampersand(self):
        assert "&amp;" in _esc("a&b")

    def test_escapes_quotes(self):
        assert "&quot;" in _esc('"hello"')

    def test_handles_non_strings(self):
        result = _esc(42)
        assert "42" in result


class TestReadSourceLines:
    """Test source line reading."""

    def test_reads_lines_around_target(self):
        # This file itself is a valid source file
        lines = _read_source_lines(__file__, 5, context=2)
        assert len(lines) > 0
        # Each entry is (lineno, text, is_error)
        for lineno, text, is_error in lines:
            assert isinstance(lineno, int)
            assert isinstance(text, str)
            assert isinstance(is_error, bool)

    def test_error_line_is_marked(self):
        lines = _read_source_lines(__file__, 5, context=2)
        error_lines = [l for l in lines if l[2]]
        assert len(error_lines) == 1
        assert error_lines[0][0] == 5

    def test_nonexistent_file_returns_empty(self):
        lines = _read_source_lines("/nonexistent/file.py", 1)
        assert lines == []


class TestSyntaxHighlight:
    """Test minimal syntax highlighting."""

    def test_highlights_keywords(self):
        result = _syntax_highlight_line("def hello():")
        assert "color:var(--mg-info)" in result

    def test_highlights_numbers(self):
        result = _syntax_highlight_line("x = 42")
        assert "color:var(--mg-green)" in result

    def test_safe_with_html_chars(self):
        result = _syntax_highlight_line("x = '<script>'")
        assert "<script>" not in result  # Should be escaped


class TestFormatCodeBlock:
    """Test code block HTML rendering."""

    def test_empty_returns_not_available(self):
        html = _format_code_block([])
        assert "source not available" in html

    def test_renders_lines(self):
        lines = [(1, "x = 1", False), (2, "y = 2", True)]
        html = _format_code_block(lines)
        assert "aq-code-block" in html
        assert "aq-line-no" in html
        assert "error-line" in html

    def test_marks_error_line(self):
        lines = [(10, "raise ValueError", True)]
        html = _format_code_block(lines)
        assert "error-line" in html


class TestFormatLocalsSection:
    """Test local variables rendering."""

    def test_empty_locals(self):
        html = _format_locals_section({})
        assert "No local variables" in html

    def test_renders_locals(self):
        html = _format_locals_section({"x": 42, "name": "hello"})
        assert "aq-locals-key" in html
        assert "42" in html
        assert "hello" in html

    def test_skips_dunder(self):
        html = _format_locals_section({"__name__": "test", "x": 1})
        assert "__name__" not in html
        assert "x" in html

    def test_truncates_long_values(self):
        html = _format_locals_section({"big": "a" * 500})
        assert "…" in html


class TestExtractFrames:
    """Test stack frame extraction from exceptions."""

    def test_extracts_frames_from_exception(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            frames = _extract_frames(e)
            assert len(frames) > 0
            frame = frames[-1]  # Last frame is where exception was raised
            assert frame['func_name'] == 'test_extracts_frames_from_exception'
            assert frame['lineno'] > 0
            assert 'filename' in frame
            assert 'locals' in frame
            assert 'source_lines' in frame

    def test_marks_app_code(self):
        try:
            raise RuntimeError("app error")
        except RuntimeError as e:
            frames = _extract_frames(e)
            # This test file should be app code (not site-packages)
            assert frames[-1]['is_app_code'] is True

    def test_nested_exception(self):
        try:
            try:
                raise TypeError("inner")
            except TypeError:
                raise ValueError("outer")
        except ValueError as e:
            frames = _extract_frames(e)
            assert len(frames) >= 1


class TestExtractRequestInfo:
    """Test request info extraction."""

    def test_none_request(self):
        info = _extract_request_info(None)
        assert info == {}

    def test_basic_request_attrs(self):
        req = MagicMock()
        req.method = "POST"
        req.path = "/api/test"
        req.query_string = "a=1"
        req.scheme = "https"
        req.headers = {"content-type": "application/json", "accept": "text/html"}
        req.cookies = {"session": "abc"}
        req.query_params = {"a": "1"}
        req.client = ("127.0.0.1", 8000)
        req.state = {"request_id": "123"}

        info = _extract_request_info(req)
        assert info['method'] == "POST"
        assert info['path'] == "/api/test"
        assert info['scheme'] == "https"
        assert 'content-type' in info['headers']
        assert info['cookies']['session'] == 'abc'


# ---------------------------------------------------------------------------
# Full page rendering tests
# ---------------------------------------------------------------------------

class TestRenderDebugExceptionPage:
    """Test the full exception debug page."""

    def _make_page(self, exc_cls=ValueError, message="test error"):
        try:
            raise exc_cls(message)
        except Exception as e:
            return render_debug_exception_page(e, aquilia_version="1.0.0")

    def test_returns_html(self):
        html = self._make_page()
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_contains_exception_type(self):
        html = self._make_page(ValueError, "bad value")
        assert "ValueError" in html

    def test_contains_exception_message(self):
        html = self._make_page(RuntimeError, "something broke")
        assert "something broke" in html

    def test_contains_mongodb_colors(self):
        html = self._make_page()
        assert "#00ED64" in html  # MongoDB green
        assert "#001E2B" in html  # MongoDB dark bg

    def test_contains_dark_light_toggle(self):
        html = self._make_page()
        assert "aq-theme-toggle" in html
        assert "aqToggleTheme" in html

    def test_contains_traceback_tab(self):
        html = self._make_page()
        assert "panel-traceback" in html
        assert "panel-request" in html
        assert "panel-raw" in html

    def test_contains_stack_frames(self):
        html = self._make_page()
        assert "aq-frame" in html

    def test_contains_source_code(self):
        html = self._make_page()
        assert "aq-code-block" in html

    def test_contains_copy_button(self):
        html = self._make_page()
        assert "aqCopyTraceback" in html
        assert "copy-btn" in html

    def test_contains_version(self):
        html = self._make_page()
        assert "v1.0.0" in html

    def test_contains_python_version(self):
        html = self._make_page()
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        assert py_ver in html

    def test_with_request(self):
        req = MagicMock()
        req.method = "GET"
        req.path = "/test"
        req.query_string = ""
        req.scheme = "http"
        req.headers = {"accept": "text/html"}
        req.cookies = {}
        req.query_params = {}
        req.client = None
        req.state = {}
        try:
            raise ValueError("with request")
        except ValueError as e:
            html = render_debug_exception_page(e, req)
        assert "GET" in html
        assert "/test" in html

    def test_escapes_xss(self):
        html = self._make_page(ValueError, "<script>alert(1)</script>")
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_with_fault_exception(self):
        """Test that Fault exceptions show domain/code/severity badges."""
        from aquilia.faults import Fault, FaultDomain, Severity
        try:
            raise Fault(
                code="TEST_FAULT",
                domain=FaultDomain.SYSTEM,
                message="fault test",
            )
        except Fault as e:
            html = render_debug_exception_page(e)
        assert "TEST_FAULT" in html
        assert "Domain:" in html


class TestRenderHttpErrorPage:
    """Test styled HTTP error pages."""

    @pytest.mark.parametrize("status,expected_title", [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (405, "Method Not Allowed"),
        (500, "Internal Server Error"),
        (502, "Bad Gateway"),
        (503, "Service Unavailable"),
    ])
    def test_renders_status_page(self, status, expected_title):
        html = render_http_error_page(status)
        assert "<!DOCTYPE html>" in html
        assert str(status) in html
        assert expected_title in html

    def test_custom_message(self):
        html = render_http_error_page(404, "Page Missing", "Could not find /api/v1/users")
        assert "Page Missing" in html
        assert "Could not find /api/v1/users" in html

    def test_contains_mongodb_theme(self):
        html = render_http_error_page(500)
        assert "#00ED64" in html
        assert "#001E2B" in html

    def test_contains_dark_light_toggle(self):
        html = render_http_error_page(404)
        assert "aq-theme-toggle" in html

    def test_with_request(self):
        req = MagicMock()
        req.method = "DELETE"
        req.path = "/api/items/42"
        html = render_http_error_page(405, request=req)
        assert "DELETE" in html
        assert "/api/items/42" in html

    def test_contains_tips_for_404(self):
        html = render_http_error_page(404)
        assert "aq routes" in html  # Tip to list routes

    def test_version_display(self):
        html = render_http_error_page(500, aquilia_version="1.0.0")
        assert "v1.0.0" in html

    def test_unknown_status(self):
        html = render_http_error_page(418)  # I'm a teapot
        assert "418" in html
        assert "Error" in html  # Fallback title

    def test_escapes_xss_in_detail(self):
        html = render_http_error_page(400, detail="<img onerror=alert(1)>")
        assert "<img" not in html
        assert "&lt;img" in html


class TestRenderWelcomePage:
    """Test the Aquilia starter welcome page."""

    def test_returns_html(self):
        html = render_welcome_page()
        assert "<!DOCTYPE html>" in html

    def test_contains_welcome_message(self):
        html = render_welcome_page()
        assert "Welcome to" in html
        assert "Aquilia" in html

    def test_contains_features(self):
        html = render_welcome_page()
        assert "Async-First" in html
        assert "Modular Architecture" in html
        assert "Fault Handling" in html

    def test_contains_quickstart(self):
        html = render_welcome_page()
        assert "aq add module" in html
        assert "Controller" in html

    def test_contains_mongodb_theme(self):
        html = render_welcome_page()
        assert "#00ED64" in html
        assert "aq-theme-toggle" in html

    def test_contains_dark_light_toggle(self):
        html = render_welcome_page()
        assert "aqToggleTheme" in html

    def test_version_display(self):
        html = render_welcome_page(aquilia_version="1.0.0")
        assert "v1.0.0" in html

    def test_contains_footer_links(self):
        html = render_welcome_page()
        assert "GitHub" in html
        assert "Documentation" in html

    def test_floating_animation(self):
        html = render_welcome_page()
        assert "aq-float" in html  # Animation keyframes

    def test_debug_flag_message(self):
        html = render_welcome_page()
        assert "debug=True" in html


class TestDebugPageRenderer:
    """Test the DebugPageRenderer class."""

    def test_render_exception(self):
        try:
            raise TypeError("renderer test")
        except TypeError as e:
            html = DebugPageRenderer.render_exception(e, aquilia_version="1.0.0")
        assert "TypeError" in html
        assert "renderer test" in html

    def test_render_http_error(self):
        html = DebugPageRenderer.render_http_error(404, "Not Found", aquilia_version="1.0.0")
        assert "404" in html

    def test_render_welcome(self):
        html = DebugPageRenderer.render_welcome(aquilia_version="1.0.0")
        assert "Welcome" in html


# ---------------------------------------------------------------------------
# ExceptionMiddleware integration tests
# ---------------------------------------------------------------------------

class TestExceptionMiddlewareDebugPages:
    """Test ExceptionMiddleware HTML debug page rendering."""

    def _make_middleware(self, debug=True):
        from aquilia.middleware import ExceptionMiddleware
        return ExceptionMiddleware(debug=debug)

    def _make_request(self, accept="text/html"):
        req = MagicMock()
        req.headers = MagicMock()
        req.headers.get = MagicMock(return_value=accept)
        req.method = "GET"
        req.path = "/test"
        req.query_string = ""
        req.scheme = "http"
        req.cookies = {}
        req.query_params = {}
        req.client = None
        req.state = {}
        return req

    @pytest.mark.asyncio
    async def test_html_500_on_exception(self):
        mw = self._make_middleware(debug=True)
        req = self._make_request("text/html")
        ctx = MagicMock()

        async def handler(r, c):
            raise RuntimeError("boom")

        response = await mw(req, ctx, handler)
        assert response.status == 500
        body = response._content if isinstance(response._content, str) else response._content.decode()
        assert "<!DOCTYPE html>" in body
        assert "RuntimeError" in body
        assert "boom" in body

    @pytest.mark.asyncio
    async def test_json_500_when_no_html_accept(self):
        mw = self._make_middleware(debug=True)
        req = self._make_request("application/json")
        ctx = MagicMock()

        async def handler(r, c):
            raise RuntimeError("boom")

        response = await mw(req, ctx, handler)
        assert response.status == 500
        # Should be JSON, not HTML
        body = response._content if isinstance(response._content, str) else response._content.decode()
        assert "<!DOCTYPE html>" not in body

    @pytest.mark.asyncio
    async def test_json_500_when_debug_off(self):
        mw = self._make_middleware(debug=False)
        req = self._make_request("text/html")
        ctx = MagicMock()

        async def handler(r, c):
            raise RuntimeError("boom")

        response = await mw(req, ctx, handler)
        assert response.status == 500
        body = response._content if isinstance(response._content, str) else response._content.decode()
        assert "<!DOCTYPE html>" not in body

    @pytest.mark.asyncio
    async def test_html_400_on_value_error(self):
        mw = self._make_middleware(debug=True)
        req = self._make_request("text/html")
        ctx = MagicMock()

        async def handler(r, c):
            raise ValueError("bad input")

        response = await mw(req, ctx, handler)
        assert response.status == 400
        body = response._content if isinstance(response._content, str) else response._content.decode()
        assert "<!DOCTYPE html>" in body
        assert "Bad Request" in body

    @pytest.mark.asyncio
    async def test_html_403_on_permission_error(self):
        mw = self._make_middleware(debug=True)
        req = self._make_request("text/html")
        ctx = MagicMock()

        async def handler(r, c):
            raise PermissionError("denied")

        response = await mw(req, ctx, handler)
        assert response.status == 403
        body = response._content if isinstance(response._content, str) else response._content.decode()
        assert "<!DOCTYPE html>" in body
        assert "Forbidden" in body

    @pytest.mark.asyncio
    async def test_html_on_fault_5xx(self):
        from aquilia.faults import Fault, FaultDomain
        mw = self._make_middleware(debug=True)
        req = self._make_request("text/html")
        ctx = MagicMock()

        async def handler(r, c):
            raise Fault(code="SYS_ERR", domain=FaultDomain.SYSTEM, message="system crash")

        response = await mw(req, ctx, handler)
        assert response.status == 500
        body = response._content if isinstance(response._content, str) else response._content.decode()
        assert "<!DOCTYPE html>" in body
        assert "SYS_ERR" in body or "system crash" in body

    @pytest.mark.asyncio
    async def test_html_on_fault_4xx(self):
        from aquilia.faults import Fault, FaultDomain
        mw = self._make_middleware(debug=True)
        req = self._make_request("text/html")
        ctx = MagicMock()

        async def handler(r, c):
            raise Fault(code="ROUTE_MISS", domain=FaultDomain.ROUTING, message="route not found")

        response = await mw(req, ctx, handler)
        assert response.status == 404
        body = response._content if isinstance(response._content, str) else response._content.decode()
        assert "<!DOCTYPE html>" in body

    @pytest.mark.asyncio
    async def test_normal_response_passes_through(self):
        from aquilia.response import Response
        mw = self._make_middleware(debug=True)
        req = self._make_request("text/html")
        ctx = MagicMock()

        async def handler(r, c):
            return Response.json({"ok": True})

        response = await mw(req, ctx, handler)
        assert response.status == 200


# ---------------------------------------------------------------------------
# CLI generator tests
# ---------------------------------------------------------------------------

class TestWorkspaceGeneratorStarterPage:
    """Test that workspace generator creates starter page."""

    def test_creates_starter_file(self, tmp_path):
        from aquilia.cli.generators.workspace import WorkspaceGenerator
        gen = WorkspaceGenerator(
            name="testapp",
            path=tmp_path / "testapp",
            minimal=False,
        )
        gen.generate()

        starter = tmp_path / "testapp" / "starter.py"
        assert starter.exists()

        content = starter.read_text()
        assert "StarterController" in content
        assert "welcome" in content
        assert "render_welcome_page" in content

    def test_starter_page_has_controller_structure(self, tmp_path):
        from aquilia.cli.generators.workspace import WorkspaceGenerator
        gen = WorkspaceGenerator(
            name="myapp",
            path=tmp_path / "myapp",
            minimal=False,
        )
        gen.generate()

        content = (tmp_path / "myapp" / "starter.py").read_text()
        assert "class StarterController(Controller):" in content
        assert '@GET("/")' in content
        assert "prefix" in content

    def test_creates_starter_even_in_minimal(self, tmp_path):
        """Starter page is created even in minimal mode."""
        from aquilia.cli.generators.workspace import WorkspaceGenerator
        gen = WorkspaceGenerator(
            name="minapp",
            path=tmp_path / "minapp",
            minimal=True,
        )
        gen.generate()

        assert (tmp_path / "minapp" / "starter.py").exists()

    def test_dev_config_has_debug_true(self, tmp_path):
        from aquilia.cli.generators.workspace import WorkspaceGenerator
        gen = WorkspaceGenerator(
            name="debugapp",
            path=tmp_path / "debugapp",
        )
        gen.generate()

        dev_yaml = (tmp_path / "debugapp" / "config" / "dev.yaml").read_text()
        assert "debug: true" in dev_yaml


# ---------------------------------------------------------------------------
# Import / export tests
# ---------------------------------------------------------------------------

class TestDebugExports:
    """Test that debug module is properly exported."""

    def test_import_from_debug_package(self):
        from aquilia.debug import (
            render_debug_exception_page,
            render_http_error_page,
            render_welcome_page,
            DebugPageRenderer,
        )
        assert callable(render_debug_exception_page)
        assert callable(render_http_error_page)
        assert callable(render_welcome_page)

    def test_import_from_aquilia(self):
        from aquilia import (
            DebugPageRenderer,
            render_debug_exception_page,
            render_http_error_page,
            render_welcome_page,
        )
        assert callable(render_debug_exception_page)

    def test_debug_page_renderer_has_methods(self):
        from aquilia.debug import DebugPageRenderer
        assert hasattr(DebugPageRenderer, 'render_exception')
        assert hasattr(DebugPageRenderer, 'render_http_error')
        assert hasattr(DebugPageRenderer, 'render_welcome')
