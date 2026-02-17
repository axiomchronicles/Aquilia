"""
Sanic Benchmark Application
============================
Parity endpoints matching Aquilia benchmark.
All business logic is identical across frameworks.

Usage:
    sanic benchmark.apps.sanic_app.main:app --host 0.0.0.0 --port 8001 --workers 4
"""
import asyncio
import json
import os
import time

import asyncpg
from jinja2 import Template
from sanic import Sanic, text, json as sanic_json
from sanic.response import html as sanic_html, raw, stream as sanic_stream
from sanic import Websocket

# ─── Config ───
DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@localhost:5432/bench")

# ─── Shared payloads (identical to Aquilia) ───
LARGE_PAYLOAD = {
    "data": [
        {"id": i, "name": f"item-{i}", "value": "x" * 200, "tags": ["a", "b", "c"]}
        for i in range(2000)
    ]
}
LARGE_PAYLOAD_BYTES = json.dumps(LARGE_PAYLOAD).encode("utf-8")

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
COMPILED_TEMPLATE = Template(TEMPLATE_HTML)

app = Sanic("SanicBench")
app.config.REQUEST_MAX_SIZE = 100_000_000  # 100 MB for upload tests


# ─── DB Pool ───
@app.before_server_start
async def setup_db(app, loop):
    app.ctx.pool = await asyncpg.create_pool(
        DB_DSN, min_size=4, max_size=8, command_timeout=10
    )


@app.after_server_stop
async def close_db(app, loop):
    if hasattr(app.ctx, "pool") and app.ctx.pool:
        await app.ctx.pool.close()


# ─── Static files ───
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static")
app.static("/static", STATIC_DIR)


# ──────────────────── 1. Ping ────────────────────
@app.get("/ping")
async def ping(request):
    return text("pong")


# ──────────────────── 2. JSON (small) ────────────
@app.get("/json")
async def json_small(request):
    return sanic_json({"hello": "world"})


# ──────────────────── 3. JSON (large) ────────────
@app.get("/json-large")
async def json_large(request):
    return sanic_json(LARGE_PAYLOAD)


# ──────────────────── 4. HTML (template) ──────────
@app.get("/html")
async def html_template(request):
    rendered = COMPILED_TEMPLATE.render(name="World", count=50, items=TEMPLATE_ITEMS)
    return sanic_html(rendered)


# ──────────────────── 5. Path param ───────────────
@app.get("/user/<user_id:int>")
async def path_param(request, user_id: int):
    return sanic_json({"id": user_id, "name": f"user-{user_id}"})


# ──────────────────── 6. Query params ─────────────
@app.get("/search")
async def query_params(request):
    result = {}
    for key in [
        "q", "page", "limit", "sort", "order", "category",
        "min_price", "max_price", "brand", "color",
        "size", "material", "rating", "in_stock",
        "free_shipping", "new_arrival", "on_sale",
        "featured", "tag", "lang",
    ]:
        result[key] = request.args.get(key, "")
    return sanic_json(result)


# ──────────────────── 7. DB read ──────────────────
@app.get("/db/<row_id:int>")
async def db_read(request, row_id: int):
    async with request.app.ctx.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, email, bio FROM bench_users WHERE id = $1", row_id
        )
    if row:
        return sanic_json(dict(row))
    return sanic_json({"error": "not found"}, status=404)


# ──────────────────── 8. DB write ─────────────────
@app.post("/db")
async def db_write(request):
    body = request.json
    async with request.app.ctx.pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO bench_users (name, email, bio) VALUES ($1, $2, $3) RETURNING id, name, email, bio",
            body.get("name", "test"),
            body.get("email", "test@example.com"),
            body.get("bio", "A benchmark user"),
        )
    return sanic_json(dict(row), status=201)


# ──────────────────── 9. Upload ───────────────────
@app.post("/upload")
async def upload(request):
    total_size = 0
    for name, file_obj in request.files.items():
        if isinstance(file_obj, list):
            for f in file_obj:
                total_size += len(f.body)
        else:
            total_size += len(file_obj.body)
    return sanic_json({"size": total_size, "status": "ok"})


# ──────────────────── 10. Stream ──────────────────
@app.get("/stream")
async def stream_response(request):
    async def generate(response):
        chunk = b"x" * 10240  # 10 KB
        for _ in range(100):  # 100 chunks = 1 MB total
            await response.write(chunk)
            await asyncio.sleep(0)
    return sanic_stream(generate, content_type="application/octet-stream")


# ──────────────────── 11. SSE ─────────────────────
@app.get("/sse")
async def sse(request):
    async def generate(response):
        for i in range(50):
            event_data = json.dumps({"seq": i, "ts": time.time()})
            msg = f"event: tick\nid: {i}\ndata: {event_data}\n\n"
            await response.write(msg.encode("utf-8"))
            await asyncio.sleep(0)
    return sanic_stream(
        generate,
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────── 12. WebSocket ───────────────
@app.websocket("/ws")
async def ws_echo(request, ws: Websocket):
    await ws.send(json.dumps({"event": "connected", "ts": time.time()}))
    async for msg in ws:
        try:
            data = json.loads(msg)
        except (json.JSONDecodeError, TypeError):
            data = {"echo": msg}
        await ws.send(json.dumps(data))


# ──────────────────── 13. Background task ─────────
@app.get("/background")
async def background(request):
    async def bg_work():
        await asyncio.sleep(0.01)

    app.add_task(bg_work())
    return sanic_json({"status": "accepted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, workers=4, access_log=False)
