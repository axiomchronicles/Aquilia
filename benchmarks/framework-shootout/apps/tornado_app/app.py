"""
Tornado benchmark app — identical endpoints for framework shootout.

Tornado uses its own event loop and blocking DB driver (psycopg2) in
a thread pool, matching its typical real-world usage.
"""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import orjson
import psycopg2
import psycopg2.pool
import tornado.ioloop
import tornado.web
import tornado.websocket

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://bench:bench@postgres:5432/bench")
db_pool = None
executor = ThreadPoolExecutor(max_workers=20)


def get_pool():
    global db_pool
    if db_pool is None:
        db_pool = psycopg2.pool.ThreadedConnectionPool(2, 20, DB_DSN)
    return db_pool


def _db_read(item_id: int):
    p = get_pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, description, price, created_at FROM items WHERE id = %s",
                (item_id,),
            )
            return cur.fetchone()
    finally:
        p.putconn(conn)


def _db_write(name, description, price):
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
            return new_id
    finally:
        p.putconn(conn)


# ── Handlers ─────────────────────────────────────────────────────────────────

class PingHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "text/plain")
        self.write("pong")


class JsonHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write(orjson.dumps({
            "message": "hello",
            "ts": datetime.now(timezone.utc).isoformat(),
        }))


class DbReadHandler(tornado.web.RequestHandler):
    async def get(self):
        item_id = int(self.get_argument("id", "1"))
        loop = tornado.ioloop.IOLoop.current()
        row = await loop.run_in_executor(executor, _db_read, item_id)
        self.set_header("Content-Type", "application/json")
        if row is None:
            self.set_status(404)
            self.write(orjson.dumps({"error": "not found"}))
        else:
            self.write(orjson.dumps({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "price": float(row[3]),
                "created_at": row[4].isoformat(),
            }))


class DbWriteHandler(tornado.web.RequestHandler):
    async def post(self):
        body = orjson.loads(self.request.body)
        name = body.get("name", "unnamed")
        description = body.get("description", "")
        price = body.get("price", 0.0)
        loop = tornado.ioloop.IOLoop.current()
        new_id = await loop.run_in_executor(executor, _db_write, name, description, price)
        self.set_status(201)
        self.set_header("Content-Type", "application/json")
        self.write(orjson.dumps({"id": new_id}))


class UploadHandler(tornado.web.RequestHandler):
    def post(self):
        files = self.request.files.get("file")
        if files:
            data = files[0].body
        else:
            data = self.request.body
        digest = hashlib.sha256(data).hexdigest()
        self.set_header("Content-Type", "application/json")
        self.write(orjson.dumps({"sha256": digest, "size": len(data)}))


class StreamHandler(tornado.web.RequestHandler):
    async def get(self):
        CHUNK = 64 * 1024
        TOTAL = 10 * 1024 * 1024
        chunk = b"X" * CHUNK
        self.set_header("Content-Type", "application/octet-stream")
        sent = 0
        while sent < TOTAL:
            to_send = min(CHUNK, TOTAL - sent)
            self.write(chunk[:to_send])
            await self.flush()
            sent += to_send
        self.finish()


class WsEchoHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def on_message(self, message):
        self.write_message(message)


# ── App ──────────────────────────────────────────────────────────────────────

def make_app():
    return tornado.web.Application([
        (r"/ping", PingHandler),
        (r"/json", JsonHandler),
        (r"/db-read", DbReadHandler),
        (r"/db-write", DbWriteHandler),
        (r"/upload", UploadHandler),
        (r"/stream", StreamHandler),
        (r"/ws-echo", WsEchoHandler),
    ], decompress_request=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(8080, address="0.0.0.0")
    print("Tornado listening on :8080")
    tornado.ioloop.IOLoop.current().start()
