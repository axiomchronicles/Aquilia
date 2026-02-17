"""
Minimal Django WSGI app for framework shootout.
Uses raw SQL (same as other frameworks) — no ORM overhead.
"""

import hashlib
import os
from datetime import datetime, timezone

import django
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.urls import path

import orjson
import psycopg2
import psycopg2.pool

# ── Django settings (minimal) ────────────────────────────────────────────────
if not settings.configured:
    settings.configure(
        DEBUG=False,
        SECRET_KEY="benchmark-secret-key-not-for-production",
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        MIDDLEWARE=[],
    )
    django.setup()

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")
pool = None


def get_pool():
    global pool
    if pool is None:
        pool = psycopg2.pool.ThreadedConnectionPool(2, 20, DB_DSN)
    return pool


# ── Views ────────────────────────────────────────────────────────────────────

def ping(request):
    return HttpResponse("pong", content_type="text/plain")


def json_view(request):
    data = orjson.dumps({
        "message": "hello",
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return HttpResponse(data, content_type="application/json")


def db_read(request):
    item_id = request.GET.get("id", "1")
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
                return HttpResponse(
                    orjson.dumps({"error": "not found"}),
                    status=404,
                    content_type="application/json",
                )
            result = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "price": float(row[3]),
                "created_at": row[4].isoformat(),
            }
            return HttpResponse(orjson.dumps(result), content_type="application/json")
    finally:
        p.putconn(conn)


def db_write(request):
    body = orjson.loads(request.body)
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
            return HttpResponse(
                orjson.dumps({"id": new_id}),
                status=201,
                content_type="application/json",
            )
    finally:
        p.putconn(conn)


def upload(request):
    f = request.FILES.get("file")
    if f is not None:
        data = f.read()
    else:
        data = request.body
    digest = hashlib.sha256(data).hexdigest()
    return HttpResponse(
        orjson.dumps({"sha256": digest, "size": len(data)}),
        content_type="application/json",
    )


def stream(request):
    CHUNK = 64 * 1024
    TOTAL = 10 * 1024 * 1024
    chunk = b"X" * CHUNK

    def generate():
        sent = 0
        while sent < TOTAL:
            to_send = min(CHUNK, TOTAL - sent)
            yield chunk[:to_send]
            sent += to_send

    return StreamingHttpResponse(generate(), content_type="application/octet-stream")


# ── URL routing ──────────────────────────────────────────────────────────────

urlpatterns = [
    path("ping", ping),
    path("json", json_view),
    path("db-read", db_read),
    path("db-write", db_write),
    path("upload", upload),
    path("stream", stream),
]

# WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
