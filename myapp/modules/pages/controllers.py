"""
Pages Module - Controllers

Showcases:
- Template rendering via Response.html()
- Dynamic HTML generation
- Navigation and breadcrumb injection
- Page content from DI services
- Lifecycle hooks (on_startup for cache warming)
- Both static pages and dynamic dashboard
"""

import time
from datetime import datetime
from aquilia import Controller, GET, POST, RequestCtx, Response
from .services import NavigationService, PageContentService


class PagesController(Controller):
    """
    Template/HTML pages controller.

    Demonstrates rendering HTML pages with dynamic content,
    navigation, and template-like patterns.

    In production, use self.render("template.html", context) with
    Jinja2 templates. Here we generate HTML directly to demonstrate
    the pattern without requiring template files.
    """

    prefix = "/"
    tags = ["pages", "templates", "frontend"]
    instantiation_mode = "singleton"

    def __init__(
        self,
        nav: NavigationService = None,
        content: PageContentService = None,
    ):
        self.nav = nav or NavigationService()
        self.content = content or PageContentService()
        self._started_at = None
        self._page_views = 0

    async def on_startup(self, ctx: RequestCtx):
        """
        Lifecycle hook: called once on server startup.

        Demonstrates cache warming / initialization.
        """
        self._started_at = datetime.utcnow().isoformat()

    async def on_request(self, ctx: RequestCtx):
        """Track page views."""
        self._page_views += 1

    # ── Pages ────────────────────────────────────────────────────────────

    @GET("/")
    async def home(self, ctx: RequestCtx):
        """
        Home page.

        GET /pages/
        Returns rendered HTML with hero section and feature cards.
        """
        page = await self.content.get_page("home")
        nav = await self.nav.get_navigation("/pages/")

        html = self._render_page(
            title=page["title"],
            nav=nav,
            content=self._render_home(page),
        )
        return Response.html(html)

    @GET("/about")
    async def about(self, ctx: RequestCtx):
        """
        About page.

        GET /pages/about
        """
        page = await self.content.get_page("about")
        nav = await self.nav.get_navigation("/pages/about")
        breadcrumbs = await self.nav.get_breadcrumbs("/pages/about")

        html = self._render_page(
            title=page["title"],
            nav=nav,
            breadcrumbs=breadcrumbs,
            content=self._render_about(page),
        )
        return Response.html(html)

    @GET("/contact")
    async def contact(self, ctx: RequestCtx):
        """
        Contact page with form.

        GET /pages/contact
        """
        page = await self.content.get_page("contact")
        nav = await self.nav.get_navigation("/pages/contact")

        html = self._render_page(
            title=page["title"],
            nav=nav,
            content=self._render_contact(page),
        )
        return Response.html(html)

    @POST("/contact")
    async def submit_contact(self, ctx: RequestCtx):
        """
        Handle contact form submission.

        POST /pages/contact
        Body: {"name": "...", "email": "...", "subject": "...", "message": "..."}
        """
        data = await ctx.json()
        # In production, send email / store in DB
        return Response.json({
            "success": True,
            "message": "Thank you for your message!",
            "data": data,
        })

    @GET("/dashboard")
    async def dashboard(self, ctx: RequestCtx):
        """
        Dashboard page showing application stats.

        GET /pages/dashboard
        Demonstrates dynamic data rendering and session awareness.
        """
        nav = await self.nav.get_navigation("/pages/dashboard")

        stats = {
            "server_started": self._started_at,
            "total_page_views": self._page_views,
            "current_time": datetime.utcnow().isoformat(),
            "session_active": ctx.session is not None,
        }

        html = self._render_page(
            title="Dashboard",
            nav=nav,
            content=self._render_dashboard(stats),
        )
        return Response.html(html)

    # ── HTML Rendering Helpers ──────────────────────────────────────────
    # In production, replace these with self.render("template.html", ctx)

    def _render_page(self, title, nav, content, breadcrumbs=None):
        """Render a full HTML page (simulates Jinja2 base template)."""
        nav_html = "".join(
            f'<a href="{item["href"]}" class="{"active" if item.get("active") else ""}">'
            f'{item["icon"]} {item["label"]}</a>'
            for item in nav
        )

        breadcrumb_html = ""
        if breadcrumbs:
            crumbs = " → ".join(
                f'<a href="{c["href"]}">{c["label"]}</a>'
                for c in breadcrumbs
            )
            breadcrumb_html = f'<div class="breadcrumbs">{crumbs}</div>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Aquilia</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               line-height: 1.6; color: #001E2B; background: #f8f9fa; }}
        nav {{ background: #001E2B; padding: 1rem 2rem; display: flex; gap: 1.5rem; }}
        nav a {{ color: #8FDFB0; text-decoration: none; font-weight: 500; }}
        nav a.active {{ color: #00ED64; border-bottom: 2px solid #00ED64; }}
        nav a:hover {{ color: #00ED64; }}
        .breadcrumbs {{ padding: 0.75rem 2rem; background: #e9ecef; font-size: 0.9rem; }}
        .breadcrumbs a {{ color: #001E2B; text-decoration: none; }}
        .breadcrumbs a:hover {{ text-decoration: underline; }}
        main {{ max-width: 1200px; margin: 2rem auto; padding: 0 2rem; }}
        .hero {{ text-align: center; padding: 4rem 2rem; background: linear-gradient(135deg, #001E2B, #023430);
                 color: white; border-radius: 12px; margin-bottom: 2rem; }}
        .hero h1 {{ font-size: 2.5rem; margin-bottom: 1rem; }}
        .hero p {{ font-size: 1.25rem; color: #8FDFB0; }}
        .features {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                     gap: 1.5rem; margin: 2rem 0; }}
        .feature {{ background: white; padding: 1.5rem; border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .feature .icon {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        .feature h3 {{ color: #001E2B; margin-bottom: 0.5rem; }}
        .section {{ background: white; padding: 2rem; border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1.5rem; }}
        .section h2 {{ color: #001E2B; margin-bottom: 1rem; border-bottom: 2px solid #00ED64;
                       padding-bottom: 0.5rem; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
        .stat {{ background: white; padding: 1.5rem; border-radius: 8px; text-align: center;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .stat .value {{ font-size: 2rem; font-weight: 700; color: #00ED64; }}
        .stat .label {{ color: #666; margin-top: 0.25rem; }}
        form {{ max-width: 600px; }}
        .form-group {{ margin-bottom: 1rem; }}
        .form-group label {{ display: block; margin-bottom: 0.25rem; font-weight: 500; }}
        .form-group input, .form-group textarea {{ width: 100%; padding: 0.75rem; border: 1px solid #ddd;
                 border-radius: 6px; font-size: 1rem; }}
        .form-group textarea {{ min-height: 120px; resize: vertical; }}
        button {{ background: #00ED64; color: #001E2B; border: none; padding: 0.75rem 2rem;
                  border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer; }}
        button:hover {{ background: #00c853; }}
        footer {{ text-align: center; padding: 2rem; color: #666; margin-top: 4rem; }}
    </style>
</head>
<body>
    <nav>{nav_html}</nav>
    {breadcrumb_html}
    <main>{content}</main>
    <footer>Built with ❤️ using Aquilia v0.2.0</footer>
</body>
</html>"""

    def _render_home(self, page):
        features = "".join(
            f'<div class="feature"><div class="icon">{f["icon"]}</div>'
            f'<h3>{f["title"]}</h3><p>{f["description"]}</p></div>'
            for f in page.get("features", [])
        )
        return f"""
        <div class="hero">
            <h1>{page["title"]}</h1>
            <p>{page["content"]}</p>
        </div>
        <div class="features">{features}</div>
        """

    def _render_about(self, page):
        sections = "".join(
            f'<div class="section"><h2>{s["heading"]}</h2><p>{s["text"]}</p></div>'
            for s in page.get("sections", [])
        )
        return f"""
        <div class="section">
            <h2>{page["title"]}</h2>
            <p>{page["content"]}</p>
        </div>
        {sections}
        """

    def _render_contact(self, page):
        fields = "".join(
            f'<div class="form-group"><label>{f["label"]}</label>'
            f'{"<textarea" if f["type"] == "textarea" else "<input type=" + chr(34) + f["type"] + chr(34)}'
            f' name="{f["name"]}" {"required" if f.get("required") else ""}>'
            f'{"</textarea>" if f["type"] == "textarea" else ""}</div>'
            for f in page.get("form_fields", [])
        )
        return f"""
        <div class="section">
            <h2>{page["title"]}</h2>
            <p>{page["content"]}</p>
            <form method="POST" action="/pages/contact" style="margin-top: 1.5rem;">
                {fields}
                <button type="submit">Send Message</button>
            </form>
        </div>
        """

    def _render_dashboard(self, stats):
        session_badge = (
            '<span style="color: #00ED64;">● Active</span>'
            if stats["session_active"]
            else '<span style="color: #999;">○ Inactive</span>'
        )
        return f"""
        <h1 style="margin-bottom: 1.5rem;">📊 Dashboard</h1>
        <div class="stats">
            <div class="stat">
                <div class="value">{stats["total_page_views"]}</div>
                <div class="label">Page Views</div>
            </div>
            <div class="stat">
                <div class="value">{session_badge}</div>
                <div class="label">Session</div>
            </div>
        </div>
        <div class="section" style="margin-top: 1.5rem;">
            <h2>Server Info</h2>
            <p><strong>Started:</strong> {stats["server_started"] or "N/A"}</p>
            <p><strong>Current Time:</strong> {stats["current_time"]}</p>
        </div>
        """
