import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, ArrowDownToLine, Shield, Globe, FileText, Zap } from 'lucide-react'

export function RequestPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <ArrowDownToLine className="w-4 h-4" />
          Core
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Request</code> class is a production-grade, <code className="text-aquilia-500">__slots__</code>-optimized HTTP request wrapper built on the ASGI scope.
          It provides async body streaming, JSON/form/multipart parsing with model validation, cookie handling, proxy-aware client IP detection,
          content negotiation, Range/conditional headers, auth/session/DI integration, and template context injection.
        </p>
      </div>

      {/* ================================================================ */}
      {/* Architecture */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Architecture</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Every HTTP request arriving through ASGI is wrapped in a single <code className="text-aquilia-500">Request</code> instance.
          The class uses <code className="text-aquilia-500">__slots__</code> with 20+ slots for memory efficiency and attribute-access speed.
          Lazy computation is used extensively — query parameters, headers, cookies, body, and parsed content are only computed on first access
          and then cached on the instance.
        </p>
        <CodeBlock language="python" filename="aquilia/request.py">{`class Request:
    __slots__ = (
        "_scope", "_receive", "_send", "_body", "_body_consumed",
        "_json_data", "_form_data", "_text", "_query_params",
        "_headers", "_cookies", "_url", "state", "_temp_files",
        "max_body_size", "max_field_count", "max_json_depth",
        "max_file_size", "form_memory_threshold", "upload_tempdir",
        "trust_proxy", "proxy_header", "proxy_trusted_ips",
    )`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Fault Types */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request Faults</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Request module defines seven fault types as subclasses of <code className="text-aquilia-500">RequestFault(Fault)</code>.
          Each carries a specific fault code integrated with the FaultEngine.
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Fault Class</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Code</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>HTTP Status</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>When Raised</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { cls: 'BadRequest', code: 'BAD_REQUEST', status: '400', when: 'Malformed form data, exceeded field count, missing boundary' },
                { cls: 'PayloadTooLarge', code: 'PAYLOAD_TOO_LARGE', status: '413', when: 'Body exceeds max_body_size or file exceeds max_file_size' },
                { cls: 'UnsupportedMediaType', code: 'UNSUPPORTED_MEDIA_TYPE', status: '415', when: 'Content-Type mismatch (e.g. calling .form() on JSON body)' },
                { cls: 'ClientDisconnect', code: 'CLIENT_DISCONNECT', status: '499', when: 'Client closes connection mid-stream' },
                { cls: 'InvalidJSON', code: 'INVALID_JSON', status: '400', when: 'Malformed JSON, depth limit exceeded, model validation failure' },
                { cls: 'InvalidHeader', code: 'INVALID_HEADER', status: '400', when: 'Control characters or injection attempts in headers' },
                { cls: 'MultipartParseError', code: 'MULTIPART_PARSE_ERROR', status: '400', when: 'python-multipart parser failure, byte mismatch' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.cls}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.code}</td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.status}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.when}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Constructor & Configuration */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Constructor & Configuration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Request is typically constructed by the ASGI adapter. You can configure class-level defaults that apply to all requests,
          or pass per-instance overrides:
        </p>
        <CodeBlock language="python" filename="constructor_params.py">{`Request(
    scope: dict,               # ASGI scope (type="http")
    receive: Callable,         # ASGI receive callable
    send: Callable = None,     # ASGI send callable (optional)
    *,
    max_body_size: int = 10 * 1024 * 1024,       # 10 MB body limit
    max_field_count: int = 1000,                  # Max form/multipart fields
    max_json_depth: int = 64,                     # Max JSON nesting depth
    max_file_size: int = 50 * 1024 * 1024,        # 50 MB per-file limit
    form_memory_threshold: int = 1024 * 1024,     # 1 MB — files larger spill to disk
    upload_tempdir: Path | None = None,           # Custom temp directory
    trust_proxy: bool = False,                    # Trust X-Forwarded-For
    proxy_header: str = "x-forwarded-for",        # Proxy header name
    proxy_trusted_ips: Set[str] | None = None,    # Trusted proxy IP set
)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Class-Level Defaults</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Every configuration parameter has a class-level default. You can subclass <code className="text-aquilia-500">Request</code> to override these globally:
        </p>
        <CodeBlock language="python" filename="custom_request.py">{`class ApiRequest(Request):
    """Custom Request with stricter limits."""
    max_body_size = 5 * 1024 * 1024       # 5 MB
    max_json_depth = 32                    # Shallower JSON
    max_file_size = 100 * 1024 * 1024     # 100 MB files
    trust_proxy = True                     # Behind load balancer
    proxy_header = "x-real-ip"
    proxy_trusted_ips = {"10.0.0.0/8", "172.16.0.0/12"}`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Core Properties */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Core Properties</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Property</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { p: 'method', t: 'str', d: 'HTTP method uppercased from scope (GET, POST, PUT, DELETE, PATCH, etc.)' },
                { p: 'http_version', t: 'str', d: 'HTTP version string ("1.0", "1.1", "2")' },
                { p: 'path', t: 'str', d: 'URL path decoded from scope["path"] (e.g. "/api/users/42")' },
                { p: 'raw_path', t: 'bytes', d: 'URL path as raw bytes, preserving percent-encoding' },
                { p: 'query_string', t: 'str', d: 'Raw query string decoded from scope (without leading ?)' },
                { p: 'client', t: 'tuple | None', d: 'Client (host, port) tuple from ASGI scope' },
                { p: 'scheme', t: 'str', d: '"http" or "https" from scope' },
                { p: 'is_secure', t: 'bool', d: 'True if scheme == "https"' },
                { p: 'server', t: 'tuple | None', d: 'Server (host, port) from scope' },
                { p: 'state', t: 'dict', d: 'Mutable per-request state dict for middleware/DI data' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.p}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ================================================================ */}
      {/* Lazy-Computed Accessors */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lazy-Computed Accessors</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          These properties are computed on first access and cached on the instance. Subsequent calls return the cached value with zero overhead.
        </p>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>query_params → MultiDict</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Parses the query string into a <code className="text-aquilia-500">MultiDict</code> (supports repeated keys like <code className="text-aquilia-500">?tag=a&tag=b</code>):
        </p>
        <CodeBlock language="python" filename="query_params.py">{`# Single value
page = request.query_params.get("page", "1")

# Multiple values
tags = request.query_params.get_all("tag")  # → ["python", "async"]

# Check existence
if "search" in request.query_params:
    ...`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>headers → Headers</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Case-insensitive header access. Built from the ASGI scope's raw header bytes with an internal <code className="text-aquilia-500">_index</code> dict:
        </p>
        <CodeBlock language="python" filename="headers.py">{`# Direct access (case-insensitive)
ct = request.headers.get("Content-Type")     # Works
ct = request.headers.get("content-type")     # Same result

# Shortcut method
ua = request.header("user-agent")            # Convenience method

# Check existence
if request.headers.has("authorization"):
    ...

# Get all values (e.g. multiple Set-Cookie)
all_vals = request.headers.get_all("set-cookie")`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>cookies → dict</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Parsed from the <code className="text-aquilia-500">Cookie</code> header using Python's <code className="text-aquilia-500">http.cookies.SimpleCookie</code>:
        </p>
        <CodeBlock language="python" filename="cookies.py">{`session_id = request.cookies.get("session_id")
theme = request.cookies.get("theme", "light")`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* URL Building */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>URL Building</h2>
        <CodeBlock language="python" filename="url_building.py">{`# Full URL: scheme + host + path + query
request.url()       # → "https://api.example.com/users?page=2"

# Base URL: scheme + host (no path/query)
request.base_url()  # → "https://api.example.com"

# Build URL for named route (resolved via router in state)
request.url_for("user_detail", user_id=42)
# → "https://api.example.com/api/users/42"

# URL object with parsing/manipulation
from aquilia._datastructures import URL
url = URL.parse(request.url())
url.path     # "/users"
url.netloc   # "api.example.com:443"
url.replace(path="/other")
url.with_query(page="3", sort="name")`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Client IP & Proxy Trust */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <Globe className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Client IP & Proxy Trust</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">client_ip()</code> method supports proxy-aware IP detection. When <code className="text-aquilia-500">trust_proxy=True</code>,
          it reads the configured proxy header (default: <code className="text-aquilia-500">X-Forwarded-For</code>) and optionally validates against trusted proxy IPs:
        </p>
        <CodeBlock language="python" filename="client_ip.py">{`# Direct client IP (no proxy trust)
ip = request.client_ip()  # → "192.168.1.100"

# With proxy trust enabled:
# X-Forwarded-For: 203.0.113.50, 10.0.0.1
# → Returns "203.0.113.50" (leftmost = real client)

# Configure in Request constructor or class-level:
Request(scope, receive,
    trust_proxy=True,
    proxy_header="x-forwarded-for",
    proxy_trusted_ips={"10.0.0.0/8", "172.16.0.0/12"}
)

# Falls back to scope["client"][0] if:
# - trust_proxy is False
# - Proxy header is missing
# - Proxy IP not in trusted set`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Content Helpers */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <FileText className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Content Helpers</h2>
        </div>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method / Property</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { m: 'content_type()', t: 'str | None', d: 'Content-Type header value (full, including params)' },
                { m: 'content_length', t: 'int | None', d: 'Content-Length as integer, or None if absent' },
                { m: 'is_json', t: 'bool', d: 'True if Content-Type starts with "application/json"' },
                { m: 'is_form', t: 'bool', d: 'True if Content-Type is "application/x-www-form-urlencoded"' },
                { m: 'is_multipart', t: 'bool', d: 'True if Content-Type starts with "multipart/"' },
                { m: 'accepts(media_type)', t: 'bool', d: 'Check if Accept header includes the given media type' },
                { m: 'wants_json', t: 'bool', d: 'True if Accept includes "application/json"' },
                { m: 'auth_header', t: 'str | None', d: 'Authorization header value' },
                { m: 'bearer_token', t: 'str | None', d: 'Extracts token from "Bearer <token>" Authorization header' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.m}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Range & Conditional Headers</h3>
        <CodeBlock language="python" filename="conditional_headers.py">{`# Range requests (file downloads)
range_header = request.range_header    # → "bytes=0-1023"

# Conditional caching headers
etag = request.if_none_match           # → '"abc123"'
since = request.if_modified_since      # → datetime or None

# Content negotiation
if request.accepts("text/html"):
    return Response.html(...)
elif request.wants_json:
    return Response.json(...)`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Body Streaming */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <Zap className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Body Reading & Streaming</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Body reading is designed for both convenience and efficiency. The body is read from the ASGI <code className="text-aquilia-500">receive</code> channel.
          Once consumed, it's cached — all subsequent calls return the cached value (idempotent).
        </p>

        <h3 className={`text-lg font-semibold mt-6 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Streaming (Memory-Efficient)</h3>
        <CodeBlock language="python" filename="streaming.py">{`# Stream raw bytes (enforces max_body_size)
async for chunk in request.iter_bytes():
    process(chunk)

# Stream decoded text
async for text_chunk in request.iter_text():
    buffer += text_chunk

# Read exact number of bytes
first_1kb = await request.readexactly(1024)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Full Body (Buffered)</h3>
        <CodeBlock language="python" filename="full_body.py">{`# Raw bytes (idempotent — cached after first call)
raw = await request.body()

# Decoded text (uses Content-Type charset, defaults to utf-8)
text = await request.text()

# Both raise PayloadTooLarge if body exceeds max_body_size
# iter_bytes() tracks cumulative size during streaming`}</CodeBlock>

        <div className={`${boxClass} mt-6`}>
          <p className={`text-sm ${isDark ? 'text-yellow-400' : 'text-yellow-700'}`}>
            <strong>⚡ Performance Note:</strong> The body is read from the ASGI channel only once. <code className="text-aquilia-500">await request.body()</code> caches
            the result in <code className="text-aquilia-500">_body</code>. Calling <code className="text-aquilia-500">body()</code> again returns the cache instantly.
            If you've already streamed via <code className="text-aquilia-500">iter_bytes()</code>, calling <code className="text-aquilia-500">body()</code> afterwards returns <code className="text-aquilia-500">b""</code>.
          </p>
        </div>
      </section>

      {/* ================================================================ */}
      {/* JSON Parsing */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>JSON Parsing & Model Validation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">json()</code> method supports depth checking, automatic model validation (Pydantic v1/v2, dataclasses),
          and uses the fastest available JSON decoder (<code className="text-aquilia-500">orjson → ujson → stdlib</code>):
        </p>
        <CodeBlock language="python" filename="json_parsing.py">{`# Basic JSON parsing
data = await request.json()

# With Pydantic v2 model validation
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

user = await request.json(model=UserCreate)
# Returns validated UserCreate instance
# Raises InvalidJSON on validation failure

# With dataclass validation
from dataclasses import dataclass

@dataclass
class Settings:
    theme: str
    notifications: bool

settings = await request.json(model=Settings)

# Custom depth limit (defense against deeply nested payloads)
data = await request.json(max_depth=16)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Model Detection Logic</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When a <code className="text-aquilia-500">model</code> parameter is passed, the framework auto-detects the validation strategy:
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Model Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Detection</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Validation Call</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { type: 'Pydantic v2', detect: 'hasattr(model, "model_validate")', call: 'model.model_validate(data)' },
                { type: 'Pydantic v1', detect: 'hasattr(model, "parse_obj")', call: 'model.parse_obj(data)' },
                { type: 'dataclass', detect: 'dataclasses.is_dataclass(model)', call: 'model(**data)' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.type}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.detect}</td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.call}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>JSON Depth Checking</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A recursive <code className="text-aquilia-500">_check_depth()</code> function walks the parsed data to enforce <code className="text-aquilia-500">max_json_depth</code> (default: 64).
          This defends against deeply nested JSON payloads that could cause stack overflow or excessive memory usage.
        </p>
      </section>

      {/* ================================================================ */}
      {/* Form & Multipart Parsing */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Form & Multipart Parsing</h2>

        <h3 className={`text-lg font-semibold mt-4 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>URL-Encoded Forms</h3>
        <CodeBlock language="python" filename="form_parsing.py">{`# Parse application/x-www-form-urlencoded
form = await request.form()

username = form.get("username")
password = form.get("password")

# Raises UnsupportedMediaType if Content-Type doesn't match
# Raises BadRequest if field count exceeds max_field_count`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Multipart Form Data</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Multipart parsing uses <code className="text-aquilia-500">python-multipart</code> with streaming and disk spilling.
          Files smaller than <code className="text-aquilia-500">form_memory_threshold</code> (default 1 MB) stay in memory;
          larger files are automatically spilled to temporary files on disk.
        </p>
        <CodeBlock language="python" filename="multipart_parsing.py">{`# Parse multipart/form-data (requires python-multipart)
form = await request.multipart()

# Access regular fields
name = form.get("name")
tags = form.get_all_fields("tags")  # Multiple values

# Access uploaded files
avatar = form.get_file("avatar")      # Single file
photos = form.get_all_files("photos") # Multiple files

# Shortcut: get just the files dict
files = await request.files()
# → {"avatar": [UploadFile(...)], "photos": [UploadFile(...), ...]}`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Streaming Multipart Internals</h3>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The internal <code className="text-aquilia-500">_parse_multipart_streaming()</code> method implements RFC 7578 compliant parsing with:
        </p>
        <ul className={`list-disc pl-6 space-y-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <li>Callback-based parser with 7 hooks: <code className="text-aquilia-500">on_part_begin</code>, <code className="text-aquilia-500">on_part_data</code>, <code className="text-aquilia-500">on_part_end</code>, <code className="text-aquilia-500">on_header_field</code>, <code className="text-aquilia-500">on_header_value</code>, <code className="text-aquilia-500">on_header_end</code>, <code className="text-aquilia-500">on_headers_finished</code></li>
          <li>Per-part size tracking with <code className="text-aquilia-500">max_file_size</code> enforcement</li>
          <li>Automatic disk spilling when data exceeds <code className="text-aquilia-500">form_memory_threshold</code></li>
          <li>Filename sanitization — removes path components, null bytes, and dangerous characters</li>
          <li>Proper cleanup on error — closes file handles, removes temp files</li>
          <li>Field count enforcement via <code className="text-aquilia-500">max_field_count</code></li>
        </ul>
      </section>

      {/* ================================================================ */}
      {/* Upload Helpers */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Upload Helpers</h2>
        <CodeBlock language="python" filename="upload_helpers.py">{`# Save uploaded file to destination
path = await request.save_upload(avatar, "/uploads/avatars/", overwrite=False)

# Stream to custom storage backend (S3, GCS, etc.)
from myapp.storage import S3UploadStore
store = S3UploadStore(bucket="uploads")
final_path = await request.stream_upload_to_store(avatar, store)
# Internally:
#   1. Generates UUID upload_id
#   2. Streams chunks via store.write_chunk(upload_id, chunk)
#   3. Calls store.finalize(upload_id, metadata) with filename/type/size
#   4. On error: calls store.abort(upload_id)`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Auth / Session / DI Integration */}
      {/* ================================================================ */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-6 h-6 text-aquilia-500" />
          <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Auth, Session & DI Integration</h2>
        </div>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Request object integrates with Aquilia's auth, session, and dependency injection systems through the <code className="text-aquilia-500">state</code> dict.
          Middleware populates these values during the request lifecycle.
        </p>

        <h3 className={`text-lg font-semibold mt-6 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Identity (Auth)</h3>
        <CodeBlock language="python" filename="auth_integration.py">{`# Get authenticated identity (set by AuthMiddleware)
identity = request.identity           # → Identity | None
is_authed = request.authenticated     # → bool

# Require authentication (raises AUTH_REQUIRED fault)
identity = request.require_identity()

# Role & scope checks
if request.has_role("admin"):
    ...
if request.has_scope("write:users"):
    ...`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Session</h3>
        <CodeBlock language="python" filename="session_integration.py">{`# Get session (set by SessionMiddleware)
session = request.session             # → Session | None
sid = request.session_id              # → str | None

# Require session (raises SESSION_REQUIRED fault)
session = request.require_session()

# Session is read/write
request.session = new_session`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Dependency Injection</h3>
        <CodeBlock language="python" filename="di_integration.py">{`# Get request-scoped DI container
container = request.container  # Looks for "di_container" or "container" in state

# Resolve a service (supports both sync and async containers)
auth_mgr = await request.resolve(AuthManager)

# Optional resolution (returns None instead of raising)
cache = await request.resolve(CacheBackend, optional=True)

# Inject multiple services at once
services = await request.inject(
    auth=AuthManager,
    session_engine=SessionEngine,
    mailer=MailService,
)
# → {"auth": <AuthManager>, "session_engine": <SessionEngine>, ...}`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Template Context */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Template Context Integration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">template_context</code> property returns a dict with auto-injected variables for template rendering.
          This is consumed by <code className="text-aquilia-500">Response.render()</code>.
        </p>
        <CodeBlock language="python" filename="template_context.py">{`# Auto-injected template variables:
ctx = request.template_context
# {
#     "request":          <Request>,
#     "identity":         <Identity | None>,
#     "session":          <Session | None>,
#     "authenticated":    True/False,
#     "is_authenticated": <bound method>,
#     "url":              "https://example.com/page",
#     "method":           "GET",
#     "path":             "/page",
#     "query_params":     {"page": "1"},
#     "flash_messages":   <bound method>,
#     "has_role":         <bound method>,
# }

# Add custom variables
request.add_template_context(title="Dashboard", user=current_user)

# Flash messages (reads and clears from session)
messages = request.flash_messages()  # → [{"level": "success", "text": "Saved"}]`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Lifecycle & Effects */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Lifecycle, Effects & Fault Reporting</h2>

        <h3 className={`text-lg font-semibold mt-4 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Effects</h3>
        <CodeBlock language="python" filename="effects.py">{`# Emit lifecycle effect
await request.emit_effect("user.login", user_id=42)

# Register before/after response callbacks
await request.before_response(my_before_hook)
await request.after_response(my_after_hook)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault Reporting</h3>
        <CodeBlock language="python" filename="fault_reporting.py">{`# Get fault context (for FaultEngine enrichment)
ctx = request.fault_context()
# → {
#     "method": "POST", "path": "/api/users",
#     "client_ip": "10.0.0.1", "user_agent": "...",
#     "identity_id": "user_42", "session_id": "sess_abc",
#     "request_id": "req_xyz", "trace_id": "trace_123",
#     "authenticated": True,
# }

# Report fault through FaultEngine with auto-enrichment
await request.report_fault(some_fault)`}</CodeBlock>

        <h3 className={`text-lg font-semibold mt-8 mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Metrics & Tracing</h3>
        <CodeBlock language="python" filename="metrics.py">{`# Distributed tracing
request.trace_id    # → from state or X-Trace-Id header
request.request_id  # → unique ID from state

# Record custom metrics
request.record_metric("api.latency", 0.045, endpoint="/users")

# Path params (set by router via state)
params = request.path_params()  # → {"user_id": "42"}`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Cleanup */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Resource Cleanup</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Request tracks temporary upload files and provides explicit cleanup:
        </p>
        <CodeBlock language="python" filename="cleanup.py">{`# Explicit cleanup (removes temp upload files)
await request.cleanup()
# - Calls FormData.cleanup() to remove tracked upload files
# - Deletes all files in _temp_files list
# - Clears _temp_files

# __del__ provides best-effort sync cleanup on garbage collection`}</CodeBlock>
      </section>

      {/* ================================================================ */}
      {/* Complete Example */}
      {/* ================================================================ */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Complete Example</h2>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Post, Get
from aquilia.response import Response
from pydantic import BaseModel


class CreateArticle(BaseModel):
    title: str
    body: str
    tags: list[str] = []


class ArticleController(Controller):
    prefix = "/api/articles"

    @Post("/")
    async def create(self, ctx):
        # Require authentication
        identity = ctx.request.require_identity()

        # Parse and validate JSON body
        article = await ctx.request.json(model=CreateArticle)

        # Access auth info
        author_id = identity.id

        # Emit lifecycle effect
        await ctx.request.emit_effect(
            "article.created",
            article_title=article.title,
            author=author_id,
        )

        return Response.json(
            {"id": 1, "title": article.title},
            status=201,
        )

    @Post("/with-image")
    async def create_with_image(self, ctx):
        # Parse multipart form
        form = await ctx.request.multipart()

        title = form.get("title")
        image = form.get_file("image")

        if image:
            path = await ctx.request.save_upload(
                image, "/uploads/articles/"
            )

        return Response.json({"title": title, "image": str(path)})

    @Get("/")
    async def list_articles(self, ctx):
        # Query parameters
        page = int(ctx.request.query_params.get("page", "1"))
        tags = ctx.request.query_params.get_all("tag")

        # Content negotiation
        if ctx.request.wants_json:
            return Response.json({"articles": [], "page": page})
        else:
            return Response.html("<h1>Articles</h1>")`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-gray-200 dark:border-white/10">
        <Link to="/docs/config/integrations" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Config Integrations</span>
        </Link>
        <Link to="/docs/request-response/response" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition-colors">
          <span>Response</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
