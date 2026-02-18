"""
Aquilia Starter Page — shown at / when debug=True.

Replace this controller with your own routes.
Delete this file once you have real endpoints.
"""

from aquilia import Controller, GET, RequestCtx, Response


class StarterController(Controller):
    """Default welcome page controller.

    Renders the built-in Aquilia welcome page using MongoDB Atlas
    colors with dark/light mode support.

    Remove this controller once you've added your own modules.
    """
    prefix = "/"
    tags = ["starter"]

    @GET("/")
    async def welcome(self, ctx: RequestCtx):
        """Render the Aquilia welcome page."""
        from aquilia.debug.pages import render_welcome_page
        try:
            from aquilia import __version__
            version = __version__
        except Exception:
            version = ""

        html = render_welcome_page(aquilia_version=version)
        return Response(
            content=html.encode("utf-8"),
            status=200,
            headers={"content-type": "text/html; charset=utf-8"},
        )
