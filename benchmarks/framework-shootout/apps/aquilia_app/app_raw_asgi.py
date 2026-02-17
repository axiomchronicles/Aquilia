"""
Aquilia benchmark app — identical endpoints for framework shootout.

Uses a minimal ASGI adapter that directly routes requests without
the full manifest/workspace system, giving the fairest raw-framework
comparison.
"""

import asyncio
import hashlib
import os
from datetime import datetime, timezone

import asyncpg
import orjson

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")
pool: asyncpg.Pool | None = None


async def _ensure_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DB_DSN, min_size=5, max_size=20)
    return pool


# ── Route handlers ───────────────────────────────────────────────────────────

async def ping(scope, receive, send):
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"text/plain")],
    })
    await send({"type": "http.response.body", "body": b"pong"})


async def json_endpoint(scope, receive, send):
    body = orjson.dumps({
        "message": "hello",
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": body})


async def db_read(scope, receive, send):
    p = await _ensure_pool()
    qs = scope.get("query_string", b"").decode()
    item_id = 1
    for part in qs.split("&"):
        if part.startswith("id="):
            item_id = int(part[3:])
            break

    row = await p.fetchrow(
        "SELECT id, name, description, price, created_at FROM items WHERE id = $1",
        item_id,
    )

    if row is None:
        body = orjson.dumps({"error": "not found"})
        status = 404
    else:
        body = orjson.dumps({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "price": float(row["price"]),
            "created_at": row["created_at"].isoformat(),
        })
        status = 200

    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": body})


async def _read_body(receive):
    """Read full request body from ASGI receive callable."""
    chunks = []
    while True:
        msg = await receive()
        body = msg.get("body", b"")
        if body:
            chunks.append(body)
        if not msg.get("more_body", False):
            break
    return b"".join(chunks)


async def db_write(scope, receive, send):
    p = await _ensure_pool()
    raw_body = await _read_body(receive)
    body = orjson.loads(raw_body)
    name = body.get("name", "unnamed")
    description = body.get("description", "")
    price = body.get("price", 0.0)
    new_id = await p.fetchval(
        "INSERT INTO items (name, description, price) VALUES ($1, $2, $3) RETURNING id",
        name, description, price,
    )
    resp = orjson.dumps({"id": new_id})
    await send({
        "type": "http.response.start",
        "status": 201,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": resp})


async def upload(scope, receive, send):
    data = await _read_body(receive)
    digest = hashlib.sha256(data).hexdigest()
    resp = orjson.dumps({"sha256": digest, "size": len(data)})
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": resp})


async def stream(scope, receive, send):
    CHUNK = 64 * 1024
    TOTAL = 10 * 1024 * 1024
    chunk = b"X" * CHUNK

    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/octet-stream")],
    })
    sent = 0
    while sent < TOTAL:
        to_send = min(CHUNK, TOTAL - sent)
        more = (sent + to_send) < TOTAL
        await send({
            "type": "http.response.body",
            "body": chunk[:to_send],
            "more_body": more,
        })
        sent += to_send


async def ws_echo(scope, receive, send):
    """Raw ASGI WebSocket echo."""
    await send({"type": "websocket.accept"})
    try:
        while True:
            msg = await receive()
            if msg["type"] == "websocket.receive":
                text = msg.get("text")
                if text is not None:
                    await send({"type": "websocket.send", "text": text})
                else:
                    await send({"type": "websocket.send", "bytes": msg.get("bytes", b"")})
            elif msg["type"] == "websocket.disconnect":
                break
    except Exception:
        pass


# ── ASGI router ──────────────────────────────────────────────────────────────

ROUTES = {
    "/ping": {"GET": ping},
    "/json": {"GET": json_endpoint},
    "/db-read": {"GET": db_read},
    "/db-write": {"POST": db_write},
    "/upload": {"POST": upload},
    "/stream": {"GET": stream},
}

WS_ROUTES = {
    "/ws-echo": ws_echo,
}


async def app(scope, receive, send):
    """Minimal ASGI application router."""
    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await _ensure_pool()
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                if pool:
                    await pool.close()
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    path = scope.get("path", "/")

    if scope["type"] == "websocket":
        handler = WS_ROUTES.get(path)
        if handler:
            await handler(scope, receive, send)
        return

    method = scope.get("method", "GET")
    route = ROUTES.get(path)
    if route and method in route:
        await route[method](scope, receive, send)
    else:
        await send({
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"text/plain")],
        })
        await send({"type": "http.response.body", "body": b"Not Found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080)
