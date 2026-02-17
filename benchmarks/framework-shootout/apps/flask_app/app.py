"""
Flask benchmark app — identical endpoints for framework shootout.
"""

import hashlib
import os
from datetime import datetime, timezone

import orjson
import psycopg2
import psycopg2.pool
from flask import Flask, Response, request, stream_with_context

app = Flask(__name__)

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")
pool = None


def get_pool():
    global pool
    if pool is None:
        pool = psycopg2.pool.ThreadedConnectionPool(2, 20, DB_DSN)
    return pool


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.route("/ping")
def ping():
    return "pong"


@app.route("/json")
def json_endpoint():
    data = orjson.dumps({
        "message": "hello",
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return Response(data, content_type="application/json")


@app.route("/db-read")
def db_read():
    item_id = request.args.get("id", "1")
    p = get_pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, description, price, created_at FROM items WHERE id = %s",
                (int(item_id),),
            )
            row = cur.fetchone()
            if row is None:
                return Response(orjson.dumps({"error": "not found"}), status=404,
                                content_type="application/json")
            result = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "price": float(row[3]),
                "created_at": row[4].isoformat(),
            }
            return Response(orjson.dumps(result), content_type="application/json")
    finally:
        p.putconn(conn)


@app.route("/db-write", methods=["POST"])
def db_write():
    body = request.get_json(force=True)
    name = body.get("name", "unnamed")
    description = body.get("description", "")
    price = body.get("price", 0.0)

    p = get_pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO items (name, description, price) VALUES (%s, %s, %s) RETURNING id",
                (name, description, price),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return Response(
                orjson.dumps({"id": new_id}),
                status=201,
                content_type="application/json",
            )
    finally:
        p.putconn(conn)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if f is None:
        # Fallback: raw body
        data = request.get_data()
    else:
        data = f.read()
    digest = hashlib.sha256(data).hexdigest()
    return Response(
        orjson.dumps({"sha256": digest, "size": len(data)}),
        content_type="application/json",
    )


@app.route("/stream")
def stream():
    CHUNK = 64 * 1024  # 64 KB
    TOTAL = 10 * 1024 * 1024  # 10 MB
    chunk = b"X" * CHUNK

    def generate():
        sent = 0
        while sent < TOTAL:
            to_send = min(CHUNK, TOTAL - sent)
            yield chunk[:to_send]
            sent += to_send

    return Response(
        stream_with_context(generate()),
        content_type="application/octet-stream",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
