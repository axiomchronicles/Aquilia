import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, ArrowUpFromLine, Shield, Zap, Send, Cookie } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function ResponsePage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <ArrowUpFromLine className="w-4 h-4" />
          Core
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Response
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Response</code> class provides factory methods for JSON, HTML, plain text, file downloads, SSE, streaming, redirects, and template rendering.
          It handles content negotiation, compression, signed cookies, security headers, background tasks, Range requests, and ASGI send with fault integration.
        </p>
      </div>

      {/* ================================================================ */}
      {/* Architecture */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Response accepts any content type — <code className="text-aquilia-500">bytes</code>, <code className="text-aquilia-500">str</code>, <code className="text-aquilia-500">dict</code>, <code className="text-aquilia-500">list</code>,
          async iterables, sync iterables, and coroutines — and sends them through ASGI with automatic serialization.
          JSON encoding uses the fastest available library: <code className="text-aquilia-500">orjson → ujson → stdlib json</code>.
        </p>
        <CodeBlock language="python" filename="aquilia/response.py">{`# Content type dispatch in _send_body():
# 1. bytes      → direct send (fast path)
# 2. str        → encode with self.encoding
# 3. dict/list  → JSON encode via _encode_body()
# 4. async iter → stream chunks with more_body=True
# 5. sync iter  → stream via run_in_executor
# 6. coroutine  → await then encode (template renders)
# 7. fallback   → str() then encode`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Response Faults */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response Faults</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Fault Class</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Code</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>When Raised</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { cls: 'ResponseStreamError', code: 'RESPONSE_STREAM_ERROR', when: 'Error during ASGI body send (e.g. connection reset)' },
                { cls: 'TemplateRenderError', code: 'TEMPLATE_RENDER_ERROR', when: 'Template coroutine raises during rendering' },
                { cls: 'InvalidHeaderError', code: 'INVALID_HEADER', when: 'Header name/value contains control characters or newlines (injection prevention)' },
                { cls: 'ClientDisconnectError', code: 'CLIENT_DISCONNECT', when: 'asyncio.CancelledError during send_asgi()' },
                { cls: 'RangeNotSatisfiableError', code: 'RANGE_NOT_SATISFIABLE', when: 'Invalid byte range for file response (416)' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.cls}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.code}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.when}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Constructor */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Constructor</h2>
        <CodeBlock language="python" filename="constructor.py">{`Response(
    content: Any = b"",         # Body content (bytes, str, dict, list, iterable, coroutine)
    status: int = 200,          # HTTP status code
    headers: dict | None = None,# Response headers
    media_type: str | None = None,  # Content-Type (auto-detected if None)
    background: BackgroundTask | None = None,  # Task to run after response sent
    encoding: str = "utf-8",    # Character encoding
    validate_headers: bool = True,  # Validate headers against injection
)`}</CodeBlock>
        <p className={`mt-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          If <code className="text-aquilia-500">media_type</code> is not specified, it's auto-detected from the content type:
          <code className="text-aquilia-500">dict/list → application/json</code>,
          <code className="text-aquilia-500">str → text/plain</code>,
          <code className="text-aquilia-500">bytes → application/octet-stream</code>.
        </p>
      </section>

      {/* ================================================================ */}
      {/* Factory Methods */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Factory Methods</h2>
        </div>

        <h3 className={`text-lg font-semibold mt-4 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.json()</h3>
        <CodeBlock language="python" filename="json_response.py">{`@classmethod
def json(cls, content, *, status=200, headers=None, **kwargs) -> Response:
    """JSON response using fastest available encoder.
    
    Encoder priority: orjson → ujson → stdlib json
    Sets Content-Type: application/json
    Pre-encodes to bytes for zero-copy ASGI send.
    """

# Usage
return Response.json({"users": [...]}, status=200)
return Response.json({"id": 42}, status=201, headers={"X-Custom": "val"})`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.html()</h3>
        <CodeBlock language="python" filename="html_response.py">{`@classmethod
def html(cls, content: str, *, status=200, headers=None) -> Response:
    """HTML response. Sets Content-Type: text/html; charset=utf-8"""

return Response.html("<h1>Hello, World!</h1>")
return Response.html(rendered_template, status=200)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.text()</h3>
        <CodeBlock language="python" filename="text_response.py">{`@classmethod
def text(cls, content: str, *, status=200, headers=None) -> Response:
    """Plain text response. Sets Content-Type: text/plain; charset=utf-8"""

return Response.text("OK")
return Response.text("Not Found", status=404)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.redirect()</h3>
        <CodeBlock language="python" filename="redirect_response.py">{`@classmethod
def redirect(cls, url: str, *, status=307, headers=None) -> Response:
    """Redirect response. Default status 307 (Temporary Redirect).
    Sets Location header to the target URL.
    """

return Response.redirect("/login")                  # 307 Temporary
return Response.redirect("/new-page", status=301)   # 301 Permanent
return Response.redirect("/dashboard", status=302)  # 302 Found`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.stream()</h3>
        <CodeBlock language="python" filename="stream_response.py">{`@classmethod
def stream(cls, generator, *, status=200, content_type="application/octet-stream",
           headers=None) -> Response:
    """Streaming response from async/sync generator.
    Chunks are sent with more_body=True until exhausted.
    """

async def generate_csv():
    yield "name,email\\n"
    async for user in db.stream_users():
        yield f"{user.name},{user.email}\\n"

return Response.stream(
    generate_csv(),
    content_type="text/csv",
    headers={"Content-Disposition": "attachment; filename=users.csv"}
)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.sse()</h3>
        <CodeBlock language="python" filename="sse_response.py">{`@classmethod
def sse(cls, generator, *, status=200, headers=None) -> Response:
    """Server-Sent Events response.
    
    Sets Content-Type: text/event-stream
    Adds Cache-Control: no-cache
    Adds X-Accel-Buffering: no (disables nginx buffering)
    
    Generator yields ServerSentEvent objects (or dicts with event/data/id/retry).
    """

from aquilia.response import ServerSentEvent

async def live_updates():
    while True:
        data = await get_latest()
        yield ServerSentEvent(
            event="update",
            data=json.dumps(data),
            id=str(uuid.uuid4()),
            retry=5000,   # Client retry interval in ms
        )
        await asyncio.sleep(1)

return Response.sse(live_updates())`}</CodeBlock>

        <div className={`${boxClass} mt-4`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>ServerSentEvent</strong> is a dataclass with <code className="text-aquilia-500">event</code>, <code className="text-aquilia-500">data</code>,
            <code className="text-aquilia-500"> id</code>, and <code className="text-aquilia-500">retry</code> fields. Its <code className="text-aquilia-500">encode()</code> method
            produces the SSE wire format: <code className="text-aquilia-500">event: update\ndata: {"{...}"}\nid: abc\n\n</code>.
          </p>
        </div>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.file()</h3>
        <CodeBlock language="python" filename="file_response.py">{`@classmethod
def file(cls, path, *, filename=None, content_type=None,
         headers=None, chunk_size=64*1024) -> Response:
    """File download response.
    
    Features:
    - Async file streaming via aiofiles (falls back to executor)
    - Content-Disposition header (attachment if filename provided)
    - Auto-detects Content-Type via mimetypes module
    - Range request support (206 Partial Content)
    - Sets Content-Length from file stat
    - Stores _file_path and _file_size for range handling
    """

# Basic file download
return Response.file("/data/report.pdf")

# With custom filename (triggers browser download dialog)
return Response.file(
    "/data/exports/2024-q1.xlsx",
    filename="quarterly_report.xlsx"
)

# Inline display (images, PDFs in browser)
return Response.file(
    "/uploads/avatar.jpg",
    content_type="image/jpeg"
)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.render()</h3>
        <CodeBlock language="python" filename="render_response.py">{`@classmethod
def render(cls, template: str, context: dict = None, *,
           status=200, headers=None, request=None) -> Response:
    """Template rendering response.
    
    Resolves the template engine from the DI container via
    request.state["di_container"]. Merges provided context with
    request.template_context (auto-injected variables).
    
    The template coroutine is set as the response content and
    awaited during _send_body().
    """

return Response.render(
    "users/profile.html",
    {"user": user, "posts": posts},
    request=ctx.request,
)

# Template context auto-includes:
# request, identity, session, authenticated, url, method, path,
# query_params, flash_messages, has_role`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Convenience Factories */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Convenience Response Factories</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Module-level factory functions for common HTTP status codes:
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Function</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Status</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { fn: 'Ok(content=None)', status: '200', d: 'Default body: {"status": "ok"}' },
                { fn: 'Created(content=None, location=None)', status: '201', d: 'Sets Location header if provided' },
                { fn: 'NoContent()', status: '204', d: 'Empty body' },
                { fn: 'BadRequest(message="Bad Request")', status: '400', d: 'JSON error response' },
                { fn: 'Unauthorized(message="Unauthorized")', status: '401', d: 'JSON error response' },
                { fn: 'Forbidden(message="Forbidden")', status: '403', d: 'JSON error response' },
                { fn: 'NotFound(message="Not Found")', status: '404', d: 'JSON error response' },
                { fn: 'InternalError(message="Internal Server Error")', status: '500', d: 'JSON error response' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.fn}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.status}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python" filename="convenience.py">{`from aquilia.response import Ok, Created, NotFound, NoContent

# Quick responses
return Ok()                                    # 200 {"status": "ok"}
return Created({"id": 42}, location="/api/users/42")  # 201 + Location
return NoContent()                             # 204 empty
return NotFound("User not found")              # 404 {"error": "User not found"}`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Fault Response */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response.from_fault()</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Creates a JSON response from a <code className="text-aquilia-500">Fault</code> object with automatic HTTP status mapping:
        </p>
        <CodeBlock language="python" filename="from_fault.py">{`response = Response.from_fault(
    fault,
    include_details=True,     # Include fault.metadata in response
    request=ctx.request,      # Adds request_id to response body
)

# Fault code → HTTP status mapping:
# AUTH_REQUIRED / AUTH_TOKEN_INVALID / AUTH_TOKEN_EXPIRED → 401
# AUTHZ_INSUFFICIENT_SCOPE / AUTHZ_FORBIDDEN             → 403
# BAD_REQUEST / SESSION_INVALID                           → 400
# PAYLOAD_TOO_LARGE                                       → 413
# UNSUPPORTED_MEDIA_TYPE                                  → 415
# NOT_FOUND                                               → 404
# METHOD_NOT_ALLOWED                                      → 405
# CONFLICT                                                → 409
# RATE_LIMIT_EXCEEDED                                     → 429
# (any other code)                                        → 500

# Response body:
# {
#     "error": "AUTH_REQUIRED",
#     "message": "Authentication required",
#     "details": {...},          # if include_details=True
#     "request_id": "req_xyz"    # if request provided
# }`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Cookie Helpers */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <Cookie className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Cookie Management</h2>
        </div>

        <h3 className={`text-lg font-semibold mt-4 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>set_cookie()</h3>
        <CodeBlock language="python" filename="set_cookie.py">{`response.set_cookie(
    name="session_id",
    value="abc123",
    max_age=3600,                    # 1 hour
    expires=datetime(2025, 12, 31),  # Absolute expiry
    path="/",                        # Cookie path
    domain=".example.com",           # Cookie domain
    secure=True,                     # HTTPS only (default)
    httponly=True,                    # No JavaScript access (default)
    samesite="Lax",                  # SameSite policy (default "Lax")
    signed=False,                    # Sign with CookieSigner
    signer=None,                     # CookieSigner instance
)

# Multiple cookies — each adds a separate Set-Cookie header
response.set_cookie("theme", "dark", httponly=False, secure=False)
response.set_cookie("lang", "en")`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>delete_cookie()</h3>
        <CodeBlock language="python" filename="delete_cookie.py">{`# Sets Max-Age=0 and Expires to epoch
response.delete_cookie("session_id")
response.delete_cookie("session_id", path="/api", domain=".example.com")`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>CookieSigner</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          HMAC-based cookie signing with key rotation support:
        </p>
        <CodeBlock language="python" filename="cookie_signer.py">{`from aquilia.response import CookieSigner

# Initialize with secret key(s) — supports key rotation
signer = CookieSigner(
    secret="current-secret-key",
    old_secrets=["previous-key-1", "previous-key-2"]
)

# Sign a value (HMAC-SHA256 + urlsafe base64)
signed = signer.sign("user_42")
# → "user_42.dGhpc19pc19hX3NpZ25hdHVyZQ=="

# Unsign (validates with current key, then falls back to old_secrets)
original = signer.unsign(signed)      # → "user_42"
signer.unsign("tampered.value")       # → None (invalid signature)

# Use with set_cookie
response.set_cookie(
    "remember_me", "user_42",
    signed=True,
    signer=signer,
)`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Header Helpers */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Header Management</h2>
        <CodeBlock language="python" filename="headers.py">{`# Set header (replaces existing)
response.set_header("X-Custom", "value")

# Add header (supports multiple values — used for Set-Cookie)
response.add_header("set-cookie", "a=1")
response.add_header("set-cookie", "b=2")
# → Two Set-Cookie headers in ASGI response

# Remove header
response.unset_header("x-custom")

# Header validation (enabled by default via validate_headers=True)
# Rejects headers with control characters (\r, \n) to prevent
# HTTP header injection attacks. Raises InvalidHeaderError.`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Caching Helpers */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Caching Helpers</h2>
        <CodeBlock language="python" filename="caching.py">{`# ETag (strong or weak)
response.set_etag("abc123")              # → ETag: "abc123"
response.set_etag("abc123", weak=True)   # → ETag: W/"abc123"

# Last-Modified
from datetime import datetime
response.set_last_modified(datetime(2025, 1, 15, 12, 0))

# Cache-Control (snake_case → kebab-case conversion)
response.cache_control(max_age=3600, public=True)
# → Cache-Control: max-age=3600, public

response.cache_control(no_cache=True, no_store=True)
# → Cache-Control: no-cache, no-store

response.cache_control(
    max_age=86400,
    s_maxage=3600,
    must_revalidate=True,
)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>ETag Utilities</h3>
        <CodeBlock language="python" filename="etag_utils.py">{`from aquilia.response import (
    generate_etag,
    generate_etag_from_file,
    check_not_modified,
    not_modified_response,
)

# Generate ETag from content bytes (SHA-256, first 32 chars)
etag = generate_etag(response_bytes)

# Generate weak ETag from file metadata (mtime + size)
etag = generate_etag_from_file("/data/report.pdf")

# Check if client cache is still valid
if check_not_modified(request, etag=etag, last_modified=mtime):
    return not_modified_response(etag=etag)  # 304 response`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Security Headers */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Security Headers</h2>
        </div>
        <CodeBlock language="python" filename="security_headers.py">{`# Apply recommended security headers in one call
response.secure_headers(
    hsts=True,                                    # Strict-Transport-Security
    hsts_max_age=31536000,                        # 1 year (default)
    csp="default-src 'self'",                     # Content-Security-Policy
    frame_options="DENY",                         # X-Frame-Options
    content_type_options=True,                    # X-Content-Type-Options: nosniff
    xss_protection=True,                          # X-XSS-Protection: 1; mode=block
    referrer_policy="strict-origin-when-cross-origin",  # Referrer-Policy
)

# Sets all of these headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# Content-Security-Policy: default-src 'self'
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Referrer-Policy: strict-origin-when-cross-origin`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Background Tasks */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Background Tasks</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Background tasks run <strong>after</strong> the response has been sent to the client. Useful for sending emails, recording analytics, or cleanup.
        </p>
        <CodeBlock language="python" filename="background_tasks.py">{`from aquilia.response import Response, CallableBackgroundTask

# Via BackgroundTask protocol (any object with async run() method)
class SendWelcomeEmail:
    def __init__(self, user_email: str):
        self.user_email = user_email
    
    async def run(self):
        await mailer.send("welcome", to=self.user_email)

response = Response.json({"status": "ok"})
response._background_tasks.append(SendWelcomeEmail("user@example.com"))

# Via CallableBackgroundTask wrapper
task = CallableBackgroundTask(
    send_analytics,           # async callable
    event="user_created",     # *args
    user_id=42,               # **kwargs
)
response._background_tasks.append(task)

# Tasks execute sequentially after ASGI body send completes
# Errors are logged but don't affect the response`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* ASGI Send */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <Send className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>ASGI Send Pipeline</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">send_asgi()</code> method is the final step that transmits the response via the ASGI protocol.
          It's optimized for performance with fast-path checks:
        </p>
        <CodeBlock language="python" filename="send_asgi.py">{`await response.send_asgi(send, request=request)

# Internal pipeline:
# 1. Handle Range request (only for file responses with _file_path)
# 2. Pre-compute content-length for bytes/str content
# 3. Prepare headers (convert to ASGI byte tuples)
# 4. Send http.response.start (status + headers)
# 5. Send body via _send_body() (type-dispatched)
# 6. Run background tasks
# 7. Wrap errors in ResponseStreamError/ClientDisconnectError`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Range Request Handling</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          For file responses, the framework automatically handles <code className="text-aquilia-500">Range: bytes=N-M</code> headers:
        </p>
        <CodeBlock language="python" filename="range_request.py">{`# Supports three range formats:
# bytes=0-499     → first 500 bytes
# bytes=500-      → from byte 500 to end
# bytes=-500      → last 500 bytes

# On valid range:
# - Sets status to 206 Partial Content
# - Adds Content-Range header: bytes 0-499/10000
# - Replaces content with _create_range_stream()
# - Uses aiofiles for async streaming (fallback: executor)

# On invalid range:
# - Raises RangeNotSatisfiableError (416)

# On malformed range:
# - Silently ignored → sends full response`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Session & Lifecycle Integration</h3>
        <CodeBlock language="python" filename="lifecycle.py">{`# Before send_asgi():
# 1. Session commit — if request has session, commits changes
# 2. before_send hooks — lifecycle coordinator callbacks

# After send_asgi():
# 3. after_send hooks — lifecycle coordinator callbacks
# 4. Metrics recording — response time, status code, bytes sent`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* ServerSentEvent */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ServerSentEvent Dataclass</h2>
        <CodeBlock language="python" filename="sse_dataclass.py">{`@dataclass
class ServerSentEvent:
    data: str                           # Event data (required)
    event: Optional[str] = None         # Event type name
    id: Optional[str] = None            # Event ID (for reconnection)
    retry: Optional[int] = None         # Client retry interval (ms)

    def encode(self) -> bytes:
        """Encode to SSE wire format."""
        # Produces:
        # event: update
        # data: {"users": 42}
        # id: evt_123
        # retry: 5000
        #
        # (terminated by double newline)

# Usage
event = ServerSentEvent(
    data='{"count": 42}',
    event="user_count",
    id="evt_001",
    retry=3000,
)
wire_bytes = event.encode()`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Complete Example */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Complete Example</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Get, Post, Delete
from aquilia.response import (
    Response, Ok, Created, NoContent, NotFound,
    CookieSigner, generate_etag, check_not_modified,
    not_modified_response,
)


signer = CookieSigner(secret="my-secret-key")


class UserController(Controller):
    prefix = "/api/users"

    @Get("/")
    async def list_users(self, ctx):
        users = await self.db.get_users()
        data = [u.to_dict() for u in users]

        # Conditional response with ETag
        content = Response.json(data)._encode_body(data)
        etag = generate_etag(content)
        if check_not_modified(ctx.request, etag=etag):
            return not_modified_response(etag=etag)

        response = Response.json(data)
        response.set_etag(etag)
        response.cache_control(max_age=60, public=True)
        return response

    @Post("/")
    async def create_user(self, ctx):
        user = await ctx.request.json(model=UserCreate)
        created = await self.db.create_user(user)

        response = Created(
            created.to_dict(),
            location=f"/api/users/{created.id}"
        )
        response.set_cookie(
            "last_created", str(created.id),
            signed=True, signer=signer,
        )
        response.secure_headers()
        return response

    @Delete("/{user_id}")
    async def delete_user(self, ctx):
        user_id = ctx.path_params["user_id"]
        deleted = await self.db.delete_user(user_id)
        if not deleted:
            return NotFound(f"User {user_id} not found")

        response = NoContent()
        response.delete_cookie("last_created")
        return response

    @Get("/stream")
    async def stream_users(self, ctx):
        async def generate():
            async for user in self.db.stream_all_users():
                yield f"data: {json.dumps(user.to_dict())}\\n\\n"

        return Response.sse(generate())`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Exports */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Module Exports</h2>
        <CodeBlock language="python" filename="__all__">{`from aquilia.response import (
    # Core
    Response,
    BackgroundTask,           # Protocol: async run()
    CallableBackgroundTask,   # Wraps async callable
    ServerSentEvent,          # SSE dataclass
    CookieSigner,             # HMAC cookie signing

    # Faults
    ResponseStreamError,
    TemplateRenderError,
    InvalidHeaderError,
    ClientDisconnectError,
    RangeNotSatisfiableError,

    # Convenience factories
    Ok, Created, NoContent,
    BadRequest, Unauthorized, Forbidden,
    NotFound, InternalError,

    # Utilities
    generate_etag,
    generate_etag_from_file,
    check_not_modified,
    not_modified_response,
)`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-gray-200 dark:border-white/10">
        <Link to="/docs/request-response/request" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Request</span>
        </Link>
        <Link to="/docs/request-response/data-structures" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <span>Data Structures</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  )
}