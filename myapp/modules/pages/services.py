"""
Pages Module - Services

Showcases:
- Page content management
- Navigation builder
- DI service with lifecycle awareness
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from aquilia.di import service


@service(scope="app")
class NavigationService:
    """
    Builds navigation data for templates.

    Demonstrates providing template context data via DI services.
    """

    def __init__(self):
        self._nav_items: List[Dict[str, Any]] = [
            {"label": "Home", "href": "/pages/", "icon": "🏠"},
            {"label": "About", "href": "/pages/about", "icon": "ℹ️"},
            {"label": "Dashboard", "href": "/pages/dashboard", "icon": "📊"},
            {"label": "Contact", "href": "/pages/contact", "icon": "✉️"},
        ]

    async def get_navigation(self, active_path: str = "") -> List[Dict[str, Any]]:
        """Get navigation items with active state."""
        return [
            {**item, "active": item["href"] == active_path}
            for item in self._nav_items
        ]

    async def get_breadcrumbs(self, path: str) -> List[Dict[str, str]]:
        """Generate breadcrumbs from path."""
        parts = [p for p in path.strip("/").split("/") if p]
        crumbs = [{"label": "Home", "href": "/pages/"}]
        current_path = "/pages"

        for part in parts:
            if part == "pages":
                continue
            current_path += f"/{part}"
            crumbs.append({
                "label": part.replace("-", " ").title(),
                "href": current_path,
            })

        return crumbs


@service(scope="app")
class PageContentService:
    """
    Static page content management.

    In production, this could load from a CMS, database, or markdown files.
    """

    def __init__(self):
        self._pages: Dict[str, Dict[str, Any]] = {
            "home": {
                "title": "Welcome to Aquilia",
                "description": "A modern Python web framework",
                "content": "Build powerful web applications with Aquilia's modular architecture.",
                "hero": True,
                "features": [
                    {
                        "title": "Modular Architecture",
                        "description": "Organize your app into focused modules with their own controllers, services, and manifests.",
                        "icon": "🧩",
                    },
                    {
                        "title": "Dependency Injection",
                        "description": "Automatic constructor injection with multiple scopes and providers.",
                        "icon": "💉",
                    },
                    {
                        "title": "Real-time WebSockets",
                        "description": "Built-in WebSocket support with rooms, events, and scaling adapters.",
                        "icon": "⚡",
                    },
                    {
                        "title": "Structured Faults",
                        "description": "Replace exceptions with domain-aware faults and recovery strategies.",
                        "icon": "🛡️",
                    },
                ],
            },
            "about": {
                "title": "About Aquilia",
                "description": "Learn about the Aquilia framework",
                "content": (
                    "Aquilia is a modern, ASGI-native Python web framework designed for "
                    "building production-grade applications. It provides a complete toolkit "
                    "including DI, sessions, auth, WebSockets, AMDL models, templates, "
                    "and structured fault handling."
                ),
                "sections": [
                    {
                        "heading": "Philosophy",
                        "text": "Convention over configuration, type safety, and developer happiness.",
                    },
                    {
                        "heading": "Architecture",
                        "text": "Workspace → Modules → Controllers + Services + Manifests.",
                    },
                    {
                        "heading": "Performance",
                        "text": "ASGI-native, async-first, with compiled URL patterns.",
                    },
                ],
            },
            "contact": {
                "title": "Contact Us",
                "description": "Get in touch with the Aquilia team",
                "content": "We'd love to hear from you!",
                "form_fields": [
                    {"name": "name", "type": "text", "label": "Your Name", "required": True},
                    {"name": "email", "type": "email", "label": "Email Address", "required": True},
                    {"name": "subject", "type": "text", "label": "Subject", "required": True},
                    {"name": "message", "type": "textarea", "label": "Message", "required": True},
                ],
            },
        }

    async def get_page(self, slug: str) -> Optional[Dict[str, Any]]:
        return self._pages.get(slug)

    async def list_pages(self) -> List[Dict[str, Any]]:
        return [
            {"slug": slug, "title": page["title"], "description": page["description"]}
            for slug, page in self._pages.items()
        ]
