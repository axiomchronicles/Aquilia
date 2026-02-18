"""
CRM Login Required — Page-level session guard.

For page (HTML) controllers use ``login_required``:

    @GET("/")
    async def dashboard(self, ctx: RequestCtx):
        if guard := login_required(ctx):
            return guard
        ...

For API/JSON controllers use Aquilia's built-in ``@authenticated`` decorator
from ``aquilia.sessions``, which raises ``AuthenticationRequiredFault``
(→ 401) when the session is not authenticated:

    from aquilia.sessions import authenticated

    @GET("/api/items")
    @authenticated
    async def api_list(self, ctx: RequestCtx):
        ...
"""

from aquilia import RequestCtx, Response

_LOGIN_URL = "/auth/login"


def login_required(ctx: RequestCtx, redirect_to: str = _LOGIN_URL) -> Response | None:
    """
    Guard for page (HTML) routes.  Returns a 302 redirect to *redirect_to*
    when the session is not authenticated, preserving the original path in
    the ``next`` query param.  Returns ``None`` when the user is logged in.
    """
    session = ctx.session
    if not session or not session.is_authenticated:
        next_url = ctx.request.path
        target = f"{redirect_to}?next={next_url}" if next_url and next_url != "/" else redirect_to
        return Response.redirect(target)
    return None
