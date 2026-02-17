"""
Aquilia Benchmark Application
=============================
Parity endpoints for framework shootout benchmark.
All business logic is identical across Aquilia, Sanic, and FastAPI.
"""
import asyncio
import os
import json
import time

import asyncpg

# ─── Aquilia Imports ───
from aquilia import Controller, GET, POST, RequestCtx, Response
from aquilia.response import ServerSentEvent

# ─── Shared config ───
DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@localhost:5432/bench")
POOL = None

# ─── Large JSON payload (generated once, ~1 MB) ───
LARGE_PAYLOAD = {
    "data": [
        {"id": i, "name": f"item-{i}", "value": "x" * 200, "tags": ["a", "b", "c"]}
        for i in range(2000)
    ]
}

# ─── Template HTML (inline for parity – no filesystem dependency) ───
TEMPLATE_HTML = """<!DOCTYPE html>
<html>
<head><title>Benchmark</title></head>
<body>
<h1>Hello, {{ name }}!</h1>
<p>Items: {{ count }}</p>
<ul>
{% for item in items %}
<li>{{ item.id }}: {{ item.name }}</li>
{% endfor %}
</ul>
</body>
</html>"""

TEMPLATE_ITEMS = [{"id": i, "name": f"item-{i}"} for i in range(50)]


async def get_pool():
    global POOL
    if POOL is None:
        POOL = await asyncpg.create_pool(
            DB_DSN, min_size=4, max_size=8, command_timeout=10
        )
    return POOL


class BenchController(Controller):
    prefix = ""
    tags = ["benchmark"]

    # ──────────────────── 1. Ping ────────────────────
    @GET("/ping")
    async def ping(self, ctx: RequestCtx):
        return Response.text("pong")

    # ──────────────────── 2. JSON (small) ────────────
    @GET("/json")
    async def json_small(self, ctx: RequestCtx):
        return Response.json({"hello": "world"})

    # ──────────────────── 3. JSON (large) ────────────
    @GET("/json-large")
    async def json_large(self, ctx: RequestCtx):
        return Response.json(LARGE_PAYLOAD)

    # ──────────────────── 4. HTML (template) ──────────
    @GET("/html")
    async def html_template(self, ctx: RequestCtx):
        # Use inline Jinja2 for benchmark parity
        from jinja2 import Template
        tmpl = Template(TEMPLATE_HTML)
        rendered = tmpl.render(name="World", count=50, items=TEMPLATE_ITEMS)
        return Response.html(rendered)

    # ──────────────────── 5. Path param ───────────────
    @GET("/user/:id")
    async def path_param(self, ctx: RequestCtx):
        params = ctx.request.path_params()
        user_id = params.get("id", "0")
        return Response.json({"id": int(user_id), "name": f"user-{user_id}"})

    # ──────────────────── 6. Query params ─────────────
    @GET("/search")
    async def query_params(self, ctx: RequestCtx):
        qp = ctx.query_params
        result = {}
        for key in ["q", "page", "limit", "sort", "order", "category",
                     "min_price", "max_price", "brand", "color",
                     "size", "material", "rating", "in_stock",
                     "free_shipping", "new_arrival", "on_sale",
                     "featured", "tag", "lang"]:
            val = qp.get(key, "")
            result[key] = val
        return Response.json(result)

    # ──────────────────── 7. DB read ──────────────────
    @GET("/db/:id")
    async def db_read(self, ctx: RequestCtx):
        params = ctx.request.path_params()
        row_id = int(params.get("id", "1"))
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, email, bio FROM bench_users WHERE id = $1",
                row_id,
            )
        if row:
            return Response.json(dict(row))
        return Response.json({"error": "not found"}, status=404)

    # ──────────────────── 8. DB write ─────────────────
    @POST("/db")
    async def db_write(self, ctx: RequestCtx):
        body = await ctx.request.json()
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO bench_users (name, email, bio) VALUES ($1, $2, $3) RETURNING id, name, email, bio",
                body.get("name", "test"),
                body.get("email", "test@example.com"),
                body.get("bio", "A benchmark user"),
            )
        return Response.json(dict(row), status=201)

    # ──────────────────── 9. Upload ───────────────────
    @POST("/upload")
    async def upload(self, ctx: RequestCtx):
        total_size = 0
        files = await ctx.request.multipart()
        for field_name, file_obj in files.files.items():
            if hasattr(file_obj, 'read'):
                data = await file_obj.read() if asyncio.iscoroutinefunction(getattr(file_obj, 'read', None)) else file_obj.read()
                total_size += len(data) if isinstance(data, (bytes, bytearray)) else 0
            elif isinstance(file_obj, list):
                for f in file_obj:
                    if hasattr(f, 'size'):
                        total_size += f.size
                    elif hasattr(f, 'read'):
                        data = f.read()
                        total_size += len(data) if isinstance(data, (bytes, bytearray)) else 0
            elif hasattr(file_obj, 'size'):
                total_size += file_obj.size
        return Response.json({"size": total_size, "status": "ok"})

    # ──────────────────── 10. Stream ──────────────────
    @GET("/stream")
    async def stream(self, ctx: RequestCtx):
        async def generate():
            chunk = b"x" * 10240  # 10 KB
            for _ in range(100):  # 100 chunks = 1 MB total
                yield chunk
                await asyncio.sleep(0)  # yield control
        return Response.stream(generate(), media_type="application/octet-stream")

    # ──────────────────── 11. SSE ─────────────────────
    @GET("/sse")
    async def sse(self, ctx: RequestCtx):
        async def events():
            for i in range(50):
                yield ServerSentEvent(
                    data=json.dumps({"seq": i, "ts": time.time()}),
                    event="tick",
                    id=str(i),
                )
                await asyncio.sleep(0)
        return Response.sse(events())

    # ──────────────────── 13. Background task ─────────
    @GET("/background")
    async def background(self, ctx: RequestCtx):
        async def bg_work():
            await asyncio.sleep(0.01)  # simulate work

        resp = Response.json({"status": "accepted"})
        resp.add_background(bg_work)
        return resp


# ─── Static file served via StaticMiddleware (configured in workspace) ───
# Endpoint: /static/bench.bin (100 KB file)

# ─── WebSocket: implemented via SocketController in ws_controller.py ───
