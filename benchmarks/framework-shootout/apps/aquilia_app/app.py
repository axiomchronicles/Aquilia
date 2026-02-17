"""
Aquilia benchmark app — using REAL Aquilia framework with AppManifest.
"""

import hashlib
import os
from datetime import datetime, timezone

import asyncpg
import orjson

from aquilia.manifest import AppManifest
from aquilia.controller import Controller, GET, POST, WS
from aquilia.controller.base import RequestCtx
from aquilia.response import Response
from aquilia.server import AquiliaServer
from aquilia.config import ConfigLoader
import logging
import sys

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("aquilia")
logger.setLevel(logging.DEBUG)



class DatabaseService:
    """Database connection pool service."""
    
    def __init__(self):
        self.pool = None
    
    async def startup(self):
        self.pool = await asyncpg.create_pool(DB_DSN, min_size=5, max_size=20)
    
    async def shutdown(self):
        if self.pool:
            await self.pool.close()
    
    async def fetch_one(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)


# Module-level database service singleton
db_service = DatabaseService()


class BenchmarkController(Controller):
    prefix = "/"
    tags = ["benchmark"]
    
    @GET("/ping")
    async def ping(self, ctx: RequestCtx):
        return Response(content=b"pong", headers={"content-type": "text/plain"})
    
    @GET("/json")
    async def json_endpoint(self, ctx: RequestCtx):
        return Response.json({
            "message": "hello",
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    
    @GET("/db-read")
    async def db_read(self, ctx: RequestCtx):
        item_id = ctx.query_params.get("id")
        if not item_id:
            return Response.json({"error": "Missing id parameter"}, status=400)
        
        row = await db_service.fetch_one(
            "SELECT id, name, description, price, created_at FROM items WHERE id = $1",
            int(item_id)
        )
        
        if row:
            result = {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "price": float(row["price"]),
                "created_at": row["created_at"].isoformat(),
            }
        else:
            result = {"error": "not found"}
        
        return Response.json(result)
    
    @POST("/db-write")
    async def db_write(self, ctx: RequestCtx):
        try:
            data = await ctx.json()
            name = data.get("name", "unnamed")
            description = data.get("description", "")
            price = data.get("price", 0.0)
            
            row = await db_service.execute(
                "INSERT INTO items (name, description, price) VALUES ($1, $2, $3) RETURNING id",
                name, description, price
            )
            
            return Response.json({"id": row["id"]}, status=201)
        except Exception as e:
            print(f"DEBUG: db-write error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise

    @POST("/upload")
    async def upload(self, ctx: RequestCtx):
        try:
            body = await ctx.request.body()
            sha = hashlib.sha256(body).hexdigest()
            return Response.json({"sha256": sha, "size": len(body)})
        except Exception as e:
            # Re-raise to let fault system handle it
            raise
    
    @GET("/stream")
    async def stream(self, ctx: RequestCtx):
        try:
            CHUNK = 64 * 1024
            TOTAL = 10 * 1024 * 1024
            chunk_data = b"X" * CHUNK
            
            async def generator():
                sent = 0
                while sent < TOTAL:
                    to_send = min(CHUNK, TOTAL - sent)
                    yield chunk_data[:to_send]
                    sent += to_send
            
            return Response.stream(generator(), media_type="application/octet-stream")
        except Exception as e:
            print(f"DEBUG: stream error: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise
    
    @WS("/ws-echo")
    async def ws_echo(self, ctx: RequestCtx):
        ws = ctx.websocket
        if not ws:
            return Response(content=b"Not a WebSocket", status=400)
        
        await ws.accept()
        try:
            async for message in ws:
                if isinstance(message, str):
                    await ws.send_text(message)
                else:
                    await ws.send_bytes(message)
        except Exception:
            pass

    # ── Regressive Scenarios ────────────────────────────────────────────────

    @GET("/query")
    async def query_bench(self, ctx: RequestCtx):
        return Response.json({
            "q": ctx.query_param("q", ""),
            "limit": int(ctx.query_param("limit", "0")),
            "offset": int(ctx.query_param("offset", "0")),
        })

    @GET("/user/{id}/info")
    async def user_info(self, ctx: RequestCtx, id: str):
        # Tests path routing
        return Response.json({"id": id})

    @GET("/json-large")
    async def json_large(self, ctx: RequestCtx):
        # 50KB+ JSON response
        data = [
            {"id": i, "name": "item", "active": True}
            for i in range(1000)
        ]
        return Response.json(data)

    @GET("/html")
    async def html_bench(self, ctx: RequestCtx):
        return Response(
            content=b"<html><body><h1>Hello World</h1></body></html>",
            headers={"content-type": "text/html"}
        )


class BenchManifest(AppManifest):
    def __init__(self):
        super().__init__(
            name="bench",
            version="1.0.0",
            controllers=["app:BenchmarkController"],
        )


config = ConfigLoader()
server = AquiliaServer(manifests=[BenchManifest], config=config)

# Attach lifecycle hooks to the app context
# We use the first (and only) app context from the registry
if server.aquilary.app_contexts:
    app_ctx = server.aquilary.app_contexts[0]
    
    async def db_startup_hook(config, container):
        logger.info("🔌 Executing DB startup hook")
        try:
            await db_service.startup()
            logger.info("✅ DB Service started")
        except Exception as e:
            logger.error(f"❌ DB Service startup failed: {e}")
            raise

    async def db_shutdown_hook(config, container):
        logger.info("🔌 Executing DB shutdown hook")
        await db_service.shutdown()

    app_ctx.on_startup = db_startup_hook
    app_ctx.on_shutdown = db_shutdown_hook
else:
    logger.error("❌ No app context found to attach lifecycle hooks!")

app = server.get_asgi_app()
