"""
Minimal Aquilia benchmark app for local performance testing.
Run with: uvicorn benchmarks.local_bench_app:app --port 8099 --loop uvloop --no-access-log
Then:  ab -n 10000 -c 50 http://127.0.0.1:8099/ping
       ab -n 10000 -c 50 http://127.0.0.1:8099/json
       ab -n 10000 -c 50 "http://127.0.0.1:8099/query?q=test&limit=10&offset=0"
       ab -n 10000 -c 50 http://127.0.0.1:8099/user/42/info
       ab -n 10000 -c 50 http://127.0.0.1:8099/html
"""
import logging
import sys

from aquilia.manifest import AppManifest
from aquilia.controller import Controller, GET
from aquilia.controller.base import RequestCtx
from aquilia.response import Response
from aquilia.server import AquiliaServer
from aquilia.config import ConfigLoader

# Suppress all logging
logging.basicConfig(level=logging.WARNING, handlers=[logging.StreamHandler(sys.stdout)])
logging.getLogger("aquilia").setLevel(logging.WARNING)

_PLAIN_TEXT_HEADERS = {"content-type": "text/plain"}
_HTML_HEADERS = {"content-type": "text/html"}


class BenchController(Controller):
    prefix = "/"

    @GET("/ping")
    async def ping(self, ctx: RequestCtx):
        return Response(content=b"pong", headers=_PLAIN_TEXT_HEADERS)

    @GET("/json")
    async def json_endpoint(self, ctx: RequestCtx):
        return Response.json({"message": "hello", "status": "ok"})

    @GET("/query")
    async def query_bench(self, ctx: RequestCtx):
        return Response.json({
            "q": ctx.query_param("q", ""),
            "limit": int(ctx.query_param("limit", "0")),
            "offset": int(ctx.query_param("offset", "0")),
        })

    @GET("/user/{id}/info")
    async def user_info(self, ctx: RequestCtx, id: str):
        return Response.json({"id": id})

    @GET("/html")
    async def html_bench(self, ctx: RequestCtx):
        return Response(
            content=b"<html><body><h1>Hello World</h1></body></html>",
            headers=_HTML_HEADERS,
        )


class BenchManifest(AppManifest):
    def __init__(self):
        super().__init__(
            name="bench",
            version="1.0.0",
            controllers=["benchmarks.local_bench_app:BenchController"],
        )


config = ConfigLoader()
server = AquiliaServer(manifests=[BenchManifest], config=config)
app = server.get_asgi_app()
