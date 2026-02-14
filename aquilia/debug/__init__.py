"""
Aquilia Debug - Beautiful development-mode error and welcome pages.

Provides React-style debug exception pages, styled HTTP error pages,
and a starter welcome page — all using MongoDB-inspired colors with
dark/light mode support.

Features:
- Full traceback with source code context and syntax highlighting
- Request info display (headers, cookies, query params, body)
- Local variables inspector per stack frame
- Dark/light mode toggle with persistent preference
- Styled HTTP error pages (400, 401, 403, 404, 405, 500)
- Aquilia starter/welcome page for new projects
"""

from .pages import (
    render_debug_exception_page,
    render_http_error_page,
    render_welcome_page,
    DebugPageRenderer,
)

__all__ = [
    "render_debug_exception_page",
    "render_http_error_page",
    "render_welcome_page",
    "DebugPageRenderer",
]
