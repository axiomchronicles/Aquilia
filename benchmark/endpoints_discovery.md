# Aquilia Endpoints Discovery & Parity Mapping

> Auto-generated from full source audit of `aquilia/` — 2026-02-17

---

## 1. Public HTTP Features Discovered

| # | Feature | Aquilia API | Controller Decorator | Response Factory | Notes |
|---|---------|------------|---------------------|-----------------|-------|
| 1 | **Ping / health** | `@GET("/ping")` | `GET` | `Response.text("pong")` | Minimal response |
| 2 | **JSON (small)** | `@GET("/json")` | `GET` | `Response.json({"hello":"world"})` | Uses orjson > ujson > stdlib |
| 3 | **JSON (large ≥1 MB)** | `@GET("/json-large")` | `GET` | `Response.json(large_payload)` | Tests serializer throughput |
| 4 | **HTML (template)** | `@GET("/html")` | `GET` | `Response.template("bench.html", ctx)` or `self.render()` | Jinja2 sandboxed engine |
| 5 | **Path param** | `@GET("/user/:id")` | `GET` | `Response.json({"id": id})` | Aquilia pattern syntax `:param` |
| 6 | **Query params** | `@GET("/search")` | `GET` | `Response.json(parsed)` | `ctx.query_params` → `MultiDict` |
| 7 | **DB read** | `@GET("/db/:id")` | `GET` | `Response.json(row)` | asyncpg single-row by PK |
| 8 | **DB write** | `@POST("/db")` | `POST` | `Response.json(row, status=201)` | asyncpg INSERT RETURNING |
| 9 | **Upload** | `@POST("/upload")` | `POST` | `Response.json({"size": n})` | `ctx.request.multipart()` streaming with disk spill |
| 10 | **Stream** | `@GET("/stream")` | `GET` | `Response.stream(gen())` | Chunked transfer, async generator |
| 11 | **SSE** | `@GET("/sse")` | `GET` | `Response.sse(gen())` | `ServerSentEvent` dataclass |
| 12 | **WebSocket** | `@socket("/ws")` `@on_message` | WS | `SocketController` | Bi-directional JSON messages |
| 13 | **Static file** | `StaticMiddleware` | middleware | Direct file serving | ETag, gzip, brotli, range, LRU cache |
| 14 | **Background task** | `Response(...).add_background(fn)` | any | `background_tasks` protocol | Fire-and-forget after response |
| 15 | **File download** | `@GET("/file")` | `GET` | `Response.file(path)` | Content-Disposition, aiofiles |
| 16 | **Redirect** | `@GET("/redir")` | `GET` | `Response.redirect(url)` | 302 default |
| 17 | **DI controller** | `@injectable` + `@GET` | `GET` | Any | Constructor injection via `Annotated[T, Inject()]` |
| 18 | **Serializer path** | `request_serializer=` / `response_serializer=` | any | Validated I/O | DRF-style field validation |
| 19 | **OpenAPI docs** | `/openapi.json`, `/docs`, `/redoc` | auto | Swagger UI / ReDoc | Auto-generated from metadata |

## 2. WebSocket Features

| Feature | Aquilia API | Notes |
|---------|------------|-------|
| Connect/Disconnect | `@on_connect` / `@on_disconnect` | Per-connection DI scope |
| Message handling | `@on_message` / `@on_event("name")` | JSON envelope protocol |
| Send event | `conn.send_event(event, payload)` | With optional ACK |
| Room join/leave | `conn.join_room()` / `conn.leave_room()` | Namespace-based |
| Broadcast | `self.broadcast(event, data)` | To all connections in namespace |
| Guards | `@guard(fn)` | Auth, rate-limit per connection |
| Adapters | `MemoryAdapter` / `RedisAdapter` | Horizontal scaling |

## 3. Middleware Features (relevant to benchmarks)

| Middleware | Effect on Benchmark |
|-----------|-------------------|
| `RequestIdMiddleware` | Adds `X-Request-ID` header |
| `CORSMiddleware` | CORS headers |
| `CompressionMiddleware` | gzip responses > threshold |
| `TimingMiddleware` | `X-Response-Time` header |
| `StaticMiddleware` | Static file serving |
| `RateLimitMiddleware` | Token bucket / sliding window |
| `CSRFMiddleware` | CSRF token validation |

## 4. Parity Mapping: Aquilia → Sanic → FastAPI

| # | Scenario | Aquilia | Sanic Equivalent | FastAPI Equivalent | Parity Notes |
|---|----------|---------|-----------------|-------------------|--------------|
| 1 | ping | `Response.text("pong")` | `text("pong")` | `PlainTextResponse("pong")` | Exact parity |
| 2 | json | `Response.json({...})` | `json({...})` | `JSONResponse({...})` | All use orjson for fairness |
| 3 | json-large | `Response.json(big)` | `json(big)` | `JSONResponse(big)` | Same 1MB payload |
| 4 | html | `Response.template(...)` | `jinja2_async.render_async(...)` | `Jinja2Templates.TemplateResponse(...)` | All use Jinja2 |
| 5 | path | `ctx.request.path_params()` | `request.match_info` | Path function param | Same response |
| 6 | query | `ctx.query_params` | `request.args` | `request.query_params` | Parse 20 params |
| 7 | db-read | asyncpg `fetchrow` | asyncpg `fetchrow` | asyncpg `fetchrow` | Same pool size (8) |
| 8 | db-write | asyncpg `execute` | asyncpg `execute` | asyncpg `execute` | Same INSERT |
| 9 | upload | `request.multipart()` streaming | `request.files` | `UploadFile` | Aquilia streams to disk; others buffer. Documented. |
| 10 | stream | `Response.stream(gen)` | `response.stream(gen)` | `StreamingResponse(gen)` | 100 × 10KB chunks |
| 11 | sse | `Response.sse(gen)` | Custom SSE impl | `sse-starlette` or custom | Aquilia has native SSE |
| 12 | websocket | `@Socket("/ws")` + `@Event("echo")` | `@app.websocket` | `@app.websocket_route` | Aquilia uses envelope protocol (`{"event":"echo","data":{...}}`); Sanic/FastAPI use raw JSON echo |
| 13 | static | `StaticMiddleware` | `app.static()` | `StaticFiles` mount | Same 100KB file |
| 14 | background | `response.add_background(fn)` | `app.add_task()` | `BackgroundTasks` | Fire-and-forget |
| 15 | di-controller | `@injectable` + constructor | Manual DI / `Inject` lib | `Depends()` | Closest semantic equivalent |

### Parity Differences Documented

1. **Upload handling**: Aquilia streams multipart to disk (spill at 1MB). Sanic buffers in memory by default. FastAPI/Starlette uses `SpooledTemporaryFile`. Documented but not a fairness issue for throughput measurement.
2. **SSE**: Aquilia has first-class `Response.sse()`. Sanic requires manual implementation. FastAPI uses `sse-starlette` package.
3. **DI**: Aquilia uses constructor injection with scoped containers. FastAPI uses `Depends()`. Sanic has no built-in DI — we use a simple factory pattern for parity.
4. **WebSocket protocol**: Aquilia uses an envelope protocol (`{"event": "echo", "data": {...}}`). Sanic/FastAPI use raw JSON echo. The `ws_bench.py` script supports both via `--protocol envelope|raw`.
5. **Static files**: Aquilia's `StaticMiddleware` includes LRU cache, brotli, range requests. Sanic/FastAPI use simpler static serving. This reflects real-world usage differences.
6. **JSON serializer**: Default variant uses each framework's default serializer. Fairness variant forces orjson everywhere.
