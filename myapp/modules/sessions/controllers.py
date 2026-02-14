"""
Sessions Module - Controllers

Showcases:
- @session.require() and @session.ensure() decorators
- Cart management via session state
- User preferences via session
- Multi-step wizard with session persistence
- Session lifecycle (create, read, update, destroy)
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .services import CartService, PreferencesService


class SessionsController(Controller):
    """
    Session showcase controller.

    Demonstrates all session patterns:
    - Viewing/managing session data
    - Shopping cart (session-backed)
    - User preferences
    - Multi-step wizard
    """

    prefix = "/"
    tags = ["sessions", "cart", "preferences"]

    def __init__(
        self,
        cart_service: CartService = None,
        pref_service: PreferencesService = None,
    ):
        self.cart = cart_service or CartService()
        self.prefs = pref_service or PreferencesService()

    # ── Session Info ─────────────────────────────────────────────────────

    @GET("/info")
    async def session_info(self, ctx: RequestCtx):
        """
        Get current session information.

        GET /sessions/info
        Shows session state, whether authenticated, etc.
        """
        session = ctx.session or {}
        return Response.json({
            "has_session": ctx.session is not None,
            "session_data": dict(session) if isinstance(session, dict) else {},
            "authenticated": session.get("authenticated", False) if isinstance(session, dict) else False,
        })

    @DELETE("/")
    async def destroy_session(self, ctx: RequestCtx):
        """
        Destroy current session.

        DELETE /sessions/
        """
        if ctx.session is not None and isinstance(ctx.session, dict):
            ctx.session.clear()
        return Response.json({"destroyed": True})

    # ── Shopping Cart ───────────────────────────────────────────────────

    @GET("/cart")
    async def view_cart(self, ctx: RequestCtx):
        """
        View shopping cart.

        GET /sessions/cart
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        cart = await self.cart.get_cart(session)
        return Response.json(cart)

    @POST("/cart/add")
    async def add_to_cart(self, ctx: RequestCtx):
        """
        Add item to cart.

        POST /sessions/cart/add
        Body: {"product_id": "prod_1", "name": "Widget", "price": 29.99, "quantity": 2}
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        data = await ctx.json()

        cart = await self.cart.add_item(
            session,
            product_id=data.get("product_id", ""),
            name=data.get("name", ""),
            price=float(data.get("price", 0)),
            quantity=int(data.get("quantity", 1)),
        )
        return Response.json(cart)

    @DELETE("/cart/«product_id:str»")
    async def remove_from_cart(self, ctx: RequestCtx, product_id: str):
        """
        Remove item from cart.

        DELETE /sessions/cart/<product_id>
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        cart = await self.cart.remove_item(session, product_id)
        return Response.json(cart)

    @DELETE("/cart")
    async def clear_cart(self, ctx: RequestCtx):
        """
        Clear entire cart.

        DELETE /sessions/cart
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        cart = await self.cart.clear_cart(session)
        return Response.json(cart)

    @POST("/cart/coupon")
    async def apply_coupon(self, ctx: RequestCtx):
        """
        Apply coupon code to cart.

        POST /sessions/cart/coupon
        Body: {"code": "SAVE10"}

        Available coupons: SAVE10, SAVE20, HALF
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        data = await ctx.json()
        code = data.get("code", "")

        result = await self.cart.apply_coupon(session, code)
        if "error" in result:
            return Response.json(result, status=400)
        return Response.json(result)

    # ── User Preferences ────────────────────────────────────────────────

    @GET("/preferences")
    async def get_preferences(self, ctx: RequestCtx):
        """
        Get user preferences.

        GET /sessions/preferences
        Returns preferences with defaults for unset values.
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        prefs = await self.prefs.get_preferences(session)
        return Response.json(prefs)

    @PUT("/preferences")
    async def update_preferences(self, ctx: RequestCtx):
        """
        Update user preferences.

        PUT /sessions/preferences
        Body: {"theme": "dark", "language": "fr", "items_per_page": 50}
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        data = await ctx.json()
        prefs = await self.prefs.update_preferences(session, data)
        return Response.json(prefs)

    @DELETE("/preferences")
    async def reset_preferences(self, ctx: RequestCtx):
        """
        Reset all preferences to defaults.

        DELETE /sessions/preferences
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        prefs = await self.prefs.reset_preferences(session)
        return Response.json({"reset": True, "preferences": prefs})

    # ── Multi-Step Wizard ───────────────────────────────────────────────

    @GET("/wizard")
    async def wizard_status(self, ctx: RequestCtx):
        """
        Get wizard progress.

        GET /sessions/wizard
        Shows current step, completed steps, and form data.
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        return Response.json({
            "current_step": session.get("wizard_step", 1),
            "total_steps": 4,
            "completed_steps": session.get("wizard_completed", []),
            "form_data": session.get("wizard_data", {}),
            "is_complete": session.get("wizard_complete", False),
        })

    @POST("/wizard/step/«step:int»")
    async def wizard_submit_step(self, ctx: RequestCtx, step: int):
        """
        Submit wizard step data.

        POST /sessions/wizard/step/<step>
        Body: { ...step-specific data... }

        Step 1: Personal info (name, email)
        Step 2: Address (street, city, zip)
        Step 3: Preferences (theme, notifications)
        Step 4: Confirmation
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        data = await ctx.json()

        # Update wizard state
        wizard_data = session.get("wizard_data", {})
        wizard_data[f"step_{step}"] = data

        completed = session.get("wizard_completed", [])
        if step not in completed:
            completed.append(step)

        session["wizard_data"] = wizard_data
        session["wizard_completed"] = completed
        session["wizard_step"] = min(step + 1, 4)
        session["wizard_complete"] = len(completed) >= 4

        return Response.json({
            "step_submitted": step,
            "next_step": min(step + 1, 4),
            "completed_steps": completed,
            "is_complete": session["wizard_complete"],
        })

    @DELETE("/wizard")
    async def wizard_reset(self, ctx: RequestCtx):
        """
        Reset wizard progress.

        DELETE /sessions/wizard
        """
        session = ctx.session if isinstance(ctx.session, dict) else {}
        session.pop("wizard_step", None)
        session.pop("wizard_completed", None)
        session.pop("wizard_data", None)
        session.pop("wizard_complete", None)
        return Response.json({"reset": True})
