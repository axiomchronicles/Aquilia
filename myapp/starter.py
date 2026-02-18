"""
Aquilia CRM — Root Controller & DB Bootstrap
=============================================
Handles the root "/" redirect and first-boot database initialization.
"""

import logging
from aquilia import Controller, GET, RequestCtx, Response

logger = logging.getLogger("crm.starter")

# Track whether DB has been initialized this session
_db_initialized = False


async def _ensure_db(ctx: RequestCtx):
    """Run DB setup on first request if tables don't exist yet."""
    global _db_initialized
    if _db_initialized:
        return

    try:
        from aquilia.db import get_database
        db = get_database()
        if db is None:
            logger.warning("Database not available — skipping table setup")
            _db_initialized = True
            return

        # Check if tables exist by querying sqlite_master
        result = await db.fetch_one(
            "SELECT count(*) as cnt FROM sqlite_master WHERE type='table' AND name='crm_users'"
        )
        if result and result.get("cnt", 0) > 0:
            _db_initialized = True
            logger.info("CRM tables already exist — skipping setup")
            return

        # Tables don't exist — create them and seed data
        logger.info("First boot detected — creating CRM tables and seeding data...")
        from modules.shared.db_setup import setup_database
        await setup_database(db)
        _db_initialized = True
        logger.info("✓ CRM database initialized successfully")

    except Exception as e:
        logger.error(f"DB setup error: {e}")
        _db_initialized = True  # Don't retry on every request


class RootController(Controller):
    """Root-level controller.

    - Redirects / to /dashboard/
    - Triggers database initialization on first request
    """
    prefix = "/"
    tags = ["root"]

    @GET("/")
    async def root_redirect(self, ctx: RequestCtx):
        """Redirect root to the CRM dashboard."""
        await _ensure_db(ctx)
        return Response(
            content=b"",
            status=302,
            headers={"location": "/dashboard/"},
        )

    @GET("/health")
    async def health_check(self, ctx: RequestCtx):
        """Health check endpoint."""
        return Response.json({"status": "ok", "app": "aquilia-crm"})
