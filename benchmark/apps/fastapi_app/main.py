"""
FastAPI Benchmark Application
==============================
Parity endpoints matching Aquilia benchmark.
All business logic is identical across frameworks.

Usage:
    uvicorn benchmark.apps.fastapi_app.main:app --host 0.0.0.0 --port 8002 --workers 4
"""
import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import (
    PlainTextResponse,
    JSONResponse,
    HTMLResponse,
    StreamingResponse,
    FileResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.background import BackgroundTasks
from jinja2 import Template

# ─── Config ───
DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@localhost:5432/bench")

# ─── Shared payloads (identical to Aquilia) ───
LARGE_PAYLOAD = {
    "data": [
        {"id": i, "name": f"item-{i}", "value": "x" * 200, "tags": ["a", "b", "c"]}
        for i in range(2000)
    ]
}

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

# ─── DB Pool (managed via lifespan) ───
pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(
        DB_DSN, min_size=4, max_size=8, command_timeout=10
    )
    yield
    if pool:
        await pool.close()


app = FastAPI(title="FastAPI Bench", lifespan=lifespan)

# ─── Static files ───
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ──────────────────── 1. Ping ────────────────────
@app.get("/ping")
async def ping():
    return PlainTextResponse("pong")


# ──────────────────── 2. JSON (small) ────────────
@app.get("/json")
async def json_small():
    return JSONResponse({"hello": "world"})


# ──────────────────── 3. JSON (large) ────────────
@app.get("/json-large")
async def json_large():
    return JSONResponse(LARGE_PAYLOAD)


# ──────────────────── 4. HTML (template) ──────────
@app.get("/html")
async def html_template():
    rendered = COMPILED_TEMPLATE.render(name="World", count=50, items=TEMPLATE_ITEMS)
    return HTMLResponse(rendered)


# ──────────────────── 5. Path param ───────────────
@app.get("/user/{user_id}")
async def path_param(user_id: int):
    return JSONResponse({"id": user_id, "name": f"user-{user_id}"})


# ──────────────────── 6. Query params ─────────────
@app.get("/search")
async def query_params(request: Request):
    result = {}
    for key in [
        "q", "page", "limit", "sort", "order", "category",
        "min_price", "max_price", "brand", "color",
        "size", "material", "rating", "in_stock",
        "free_shipping", "new_arrival", "on_sale",
        "featured", "tag", "lang",
    ]:
        result[key] = request.query_params.get(key, "")
    return JSONResponse(result)


# ──────────────────── 7. DB read ──────────────────
@app.get("/db/{row_id}")
async def db_read(row_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, email, bio FROM bench_users WHERE id = $1", row_id
        )
    if row:
        return JSONResponse(dict(row))
    return JSONResponse({"error": "not found"}, status_code=404)


# ──────────────────── 8. DB write ─────────────────
@app.post("/db", status_code=201)
async def db_write(request: Request):
    body = await request.json()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO bench_users (name, email, bio) VALUES ($1, $2, $3) RETURNING id, name, email, bio",
            body.get("name", "test"),
            body.get("email", "test@example.com"),
            body.get("bio", "A benchmark user"),
        )
    return JSONResponse(dict(row), status_code=201)


# ──────────────────── 9. Upload ───────────────────
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    total_size = len(contents)
    return JSONResponse({"size": total_size, "status": "ok"})


# ──────────────────── 10. Stream ──────────────────
@app.get("/stream")
async def stream_response():
    async def generate():
        chunk = b"x" * 10240  # 10 KB
        for _ in range(100):  # 100 chunks = 1 MB total
            yield chunk
            await asyncio.sleep(0)

    return StreamingResponse(generate(), media_type="application/octet-stream")


# ──────────────────── 11. SSE ─────────────────────
@app.get("/sse")
async def sse():
    async def generate():
        for i in range(50):
            event_data = json.dumps({"seq": i, "ts": time.time()})
            yield f"event: tick\nid: {i}\ndata: {event_data}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────── 12. WebSocket ───────────────
@app.websocket("/ws")
async def ws_echo(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"event": "connected", "ts": time.time()})
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except (json.JSONDecodeError, TypeError):
                data = {"echo": msg}
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass


# ──────────────────── 13. Background task ─────────
@app.get("/background")
async def background(background_tasks: BackgroundTasks):
    async def bg_work():
        await asyncio.sleep(0.01)

    background_tasks.add_task(bg_work)
    return JSONResponse({"status": "accepted"})
