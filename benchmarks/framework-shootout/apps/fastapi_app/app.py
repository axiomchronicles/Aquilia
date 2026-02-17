"""
FastAPI benchmark app — identical endpoints for framework shootout.
"""

import asyncio
import hashlib
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import asyncpg
import orjson
from fastapi import FastAPI, File, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import ORJSONResponse, Response, StreamingResponse

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")
pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(DB_DSN, min_size=5, max_size=20)
    yield
    await pool.close()


app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/ping")
async def ping():
    return Response(content="pong", media_type="text/plain")


@app.get("/json")
async def json_endpoint():
    return {
        "message": "hello",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/db-read")
async def db_read(id: int = Query(default=1)):
    row = await pool.fetchrow(
        "SELECT id, name, description, price, created_at FROM items WHERE id = $1",
        id,
    )
    if row is None:
        return ORJSONResponse({"error": "not found"}, status_code=404)
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "price": float(row["price"]),
        "created_at": row["created_at"].isoformat(),
    }


@app.post("/db-write", status_code=201)
async def db_write(request: Request):
    body = await request.json()
    name = body.get("name", "unnamed")
    description = body.get("description", "")
    price = body.get("price", 0.0)
    new_id = await pool.fetchval(
        "INSERT INTO items (name, description, price) VALUES ($1, $2, $3) RETURNING id",
        name, description, price,
    )
    return {"id": new_id}


@app.post("/upload")
async def upload(request: Request):
    content_type = request.headers.get("content-type", "")
    if "multipart" in content_type:
        form = await request.form()
        f = form.get("file")
        data = await f.read()
    else:
        data = await request.body()
    digest = hashlib.sha256(data).hexdigest()
    return {"sha256": digest, "size": len(data)}


@app.get("/stream")
async def stream():
    CHUNK = 64 * 1024
    TOTAL = 10 * 1024 * 1024
    chunk = b"X" * CHUNK

    async def generate():
        sent = 0
        while sent < TOTAL:
            to_send = min(CHUNK, TOTAL - sent)
            yield chunk[:to_send]
            sent += to_send

    return StreamingResponse(generate(), media_type="application/octet-stream")


@app.websocket("/ws-echo")
async def ws_echo(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text(data)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
