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

# Configure logging — WARNING level for benchmarks to avoid log I/O overhead
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("aquilia")
logger.setLevel(logging.WARNING)



class DatabaseService:
    """Database connection pool service with prepared statements."""
    
    def __init__(self):
        self.pool = None
        self._read_stmt_cache = {}
        self._write_stmt_cache = {}
    
    async def startup(self):
        self.pool = await asyncpg.create_pool(
            DB_DSN,
            min_size=10,
            max_size=20,
            command_timeout=30,
            max_inactive_connection_lifetime=300,
        )
    
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


# Pre-built headers for common responses
_PLAIN_TEXT_HEADERS = {"content-type": "text/plain"}
_HTML_HEADERS = {"content-type": "text/html"}

# Pre-allocated streaming data
_STREAM_CHUNK_SIZE = 64 * 1024
_STREAM_TOTAL = 10 * 1024 * 1024
_STREAM_CHUNK = b"X" * _STREAM_CHUNK_SIZE


class BenchmarkController(Controller):
    prefix = "/"
    tags = ["benchmark"]
    
    @GET("/ping")
    async def ping(self, ctx: RequestCtx):
        return Response(content=b"pong", headers=_PLAIN_TEXT_HEADERS)
    
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
        
        try:
            row = await db_service.fetch_one(
                "SELECT id, name, description, price, created_at FROM items WHERE id = $1",
                int(item_id)
            )
        except (ValueError, TypeError):
            return Response.json({"error": "Invalid id"}, status=400)
        except Exception:
            return Response.json({"error": "Database error"}, status=503)
        
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
        except Exception:
            return Response.json({"error": "Write failed"}, status=503)

    @POST("/upload")
    async def upload(self, ctx: RequestCtx):
        body = await ctx.request.body()
        sha = hashlib.sha256(body).hexdigest()
        return Response.json({"sha256": sha, "size": len(body)})
    
    @GET("/stream")
    async def stream(self, ctx: RequestCtx):
        async def generator():
            sent = 0
            while sent < _STREAM_TOTAL:
                to_send = min(_STREAM_CHUNK_SIZE, _STREAM_TOTAL - sent)
                yield _STREAM_CHUNK[:to_send]
                sent += to_send
        
        return Response.stream(generator(), media_type="application/octet-stream")
    
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
            headers=_HTML_HEADERS
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
