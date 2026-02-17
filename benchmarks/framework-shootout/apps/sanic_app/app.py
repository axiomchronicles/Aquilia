"""
Sanic benchmark app — identical endpoints for framework shootout.
"""

import hashlib
import os
from datetime import datetime, timezone

import asyncpg
import orjson
from sanic import Sanic, json as sanic_json, text
from sanic.response import raw, ResponseStream
from sanic import Websocket

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")

app = Sanic("bench")
app.config.REQUEST_MAX_SIZE = 50_000_000  # 50 MB


@app.before_server_start
async def setup_db(app, loop):
    app.ctx.pool = await asyncpg.create_pool(DB_DSN, min_size=5, max_size=20)


@app.after_server_stop
async def close_db(app, loop):
    await app.ctx.pool.close()


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/ping")
async def ping(request):
    return text("pong")


@app.get("/json")
async def json_endpoint(request):
    return raw(
        orjson.dumps({
            "message": "hello",
            "ts": datetime.now(timezone.utc).isoformat(),
        }),
        content_type="application/json",
    )


@app.get("/db-read")
async def db_read(request):
    item_id = int(request.args.get("id", "1"))
    row = await app.ctx.pool.fetchrow(
        "SELECT id, name, description, price, created_at FROM items WHERE id = $1",
        item_id,
    )
    if row is None:
        return raw(orjson.dumps({"error": "not found"}), status=404,
                    content_type="application/json")
    result = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "price": float(row["price"]),
        "created_at": row["created_at"].isoformat(),
    }
    return raw(orjson.dumps(result), content_type="application/json")


@app.post("/db-write")
async def db_write(request):
    body = request.json
    name = body.get("name", "unnamed")
    description = body.get("description", "")
    price = body.get("price", 0.0)
    new_id = await app.ctx.pool.fetchval(
        "INSERT INTO items (name, description, price) VALUES ($1, $2, $3) RETURNING id",
        name, description, price,
    )
    return raw(orjson.dumps({"id": new_id}), status=201,
               content_type="application/json")


@app.post("/upload")
async def upload(request):
    f = request.files.get("file")
    if f:
        data = f.body
    else:
        data = request.body
    digest = hashlib.sha256(data).hexdigest()
    return raw(
        orjson.dumps({"sha256": digest, "size": len(data)}),
        content_type="application/json",
    )


@app.get("/stream")
async def stream_endpoint(request):
    CHUNK = 64 * 1024
    TOTAL = 10 * 1024 * 1024
    chunk = b"X" * CHUNK

    async def streaming(response: ResponseStream):
        sent = 0
        while sent < TOTAL:
            to_send = min(CHUNK, TOTAL - sent)
            await response.write(chunk[:to_send])
            sent += to_send

    return ResponseStream(streaming, content_type="application/octet-stream")


@app.websocket("/ws-echo")
async def ws_echo(request, ws: Websocket):
    async for msg in ws:
        await ws.send(msg)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, single_process=True)
