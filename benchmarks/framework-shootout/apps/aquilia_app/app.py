"""
Aquilia benchmark app — using REAL Aquilia framework with AppManifest.
"""

import hashlib
import os
from datetime import datetime, timezone

import asyncpg
import orjson

from aquilia.manifest import AppManifest, DatabaseConfig
from aquilia.controller import Controller, GET, POST, WS
from aquilia.controller.base import RequestCtx
from aquilia.response import Response
from aquilia.server import AquiliaServer
from aquilia.config import ConfigLoader


DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")


class DatabaseService:
    """Database connection pool service — injected via DI."""
    
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


class BenchmarkController(Controller):
    prefix = "/"
    tags = ["benchmark"]
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
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
        
        row = await self.db.fetch_one(
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
        data = await ctx.json()
        name = data.get("name", "unnamed")
        description = data.get("description", "")
        price = data.get("price", 0.0)
        
        row = await self.db.execute(
            "INSERT INTO items (name, description, price) VALUES ($1, $2, $3) RETURNING id",
            name, description, price
        )
        
        return Response.json({"id": row["id"]}, status=201)
    
    @POST("/upload")
    async def upload(self, ctx: RequestCtx):
        body = await ctx.body()
        sha = hashlib.sha256(body).hexdigest()
        return Response.json({"sha256": sha, "size": len(body)})
    
    @GET("/stream")
    async def stream(self, ctx: RequestCtx):
        CHUNK = 64 * 1024
        TOTAL = 10 * 1024 * 1024
        chunk_data = b"X" * CHUNK
        
        async def generator():
            sent = 0
            while sent < TOTAL:
                to_send = min(CHUNK, TOTAL - sent)
                yield chunk_data[:to_send]
                sent += to_send
        
        return Response.stream(generator(), content_type="application/octet-stream")
    
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


class BenchManifest(AppManifest):
    name = "bench"
    version = "1.0.0"
    
    controllers = ["app:BenchmarkController"]
    services = ["app:DatabaseService"]


config = ConfigLoader()
server = AquiliaServer(manifests=[BenchManifest], config=config)

db_service_instance = None

async def on_startup():
    global db_service_instance
    db_service_instance = server.runtime_registry.container.get(DatabaseService)
    await db_service_instance.startup()

async def on_shutdown():
    if db_service_instance:
        await db_service_instance.shutdown()

server.lifecycle.on_startup(on_startup)
server.lifecycle.on_shutdown(on_shutdown)

app = server.get_asgi_app()
