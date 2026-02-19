import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Plug, Shield, Database, Mail, Cpu, Eye, FileText, Zap, ArrowRight, AlertCircle, Globe, Layout, Lock } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function ConfigIntegrations() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Plug className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                Integrations
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.config_builders.Integration — Subsystem configuration factories</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>Integration</code> class provides static factory methods that produce configuration
          dictionaries for each Aquilia subsystem. These are passed to <code>Workspace.integrate()</code>
          to wire subsystems into the application.
        </p>
      </div>

      {/* Overview Table */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Available Integrations
        </h2>

        <div className={`overflow-x-auto mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Integration</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type Marker</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['Integration.auth()', '(legacy)', 'Authentication — JWT tokens, stores, security policies'],
                ['Integration.sessions()', '(legacy)', 'Session management — policies, stores, transport'],
                ['Integration.database()', '(legacy)', 'Database — URL, connection pool, migrations, AMDL'],
                ['Integration.di()', '(legacy)', 'Dependency injection — auto-wiring'],
                ['Integration.openapi()', '"openapi"', 'OpenAPI spec generation, Swagger UI, ReDoc'],
                ['Integration.cache()', '"cache"', 'Caching — memory, Redis, composite L1+L2'],
                ['Integration.cors()', '"cors"', 'CORS middleware'],
                ['Integration.csp()', '"csp"', 'Content-Security-Policy middleware'],
                ['Integration.csrf()', '"csrf"', 'CSRF protection middleware'],
                ['Integration.rate_limit()', '"rate_limit"', 'Rate limiting middleware'],
                ['Integration.static_files()', '"static_files"', 'Static file serving'],
                ['Integration.logging()', '"logging"', 'Request/response logging middleware'],
                ['Integration.mail()', '"mail"', 'AquilaMail — async mail subsystem'],
                ['Integration.mlops()', '"mlops"', 'MLOps platform — model registry, serving, drift'],
                ['Integration.serializers()', '"serializers"', 'Global serializer settings'],
                ['Integration.templates', '(legacy)', 'Template engine — fluent builder class'],
                ['Integration.routing()', '(legacy)', 'Routing configuration'],
                ['Integration.fault_handling()', '(legacy)', 'Fault handling defaults'],
                ['Integration.registry()', '(legacy)', 'Registry configuration'],
                ['Integration.patterns()', '(legacy)', 'Pattern matching configuration'],
              ].map(([method, marker, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{method}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{marker}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={`p-4 rounded-lg border ${isDark ? 'bg-blue-500/5 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-800'}`}>
            <AlertCircle className="w-4 h-4 inline mr-1" />
            Integrations marked <strong>(legacy)</strong> are detected by heuristic key inspection.
            Modern integrations include an <code>_integration_type</code> key for unambiguous detection
            in <code>Workspace.integrate()</code>.
          </p>
        </div>
      </section>

      {/* Auth */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Lock className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.auth()
        </h2>

        <CodeBlock language="python" title="Signature">
{`@staticmethod
def auth(
    config: Optional[AuthConfig] = None,
    enabled: bool = True,
    store_type: str = "memory",
    secret_key: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:`}
        </CodeBlock>

        <p className={`mb-4 mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Accepts either an <code>AuthConfig</code> dataclass or individual parameters. The <code>AuthConfig</code>
          dataclass provides full control:
        </p>

        <CodeBlock language="python" title="AuthConfig Dataclass">
{`@dataclass
class AuthConfig:
    enabled: bool = True
    store_type: str = "memory"
    secret_key: Optional[str] = None   # MUST be set explicitly; no insecure default
    algorithm: str = "HS256"
    issuer: str = "aquilia"
    audience: str = "aquilia-app"
    access_token_ttl_minutes: int = 60
    refresh_token_ttl_days: int = 30
    require_auth_by_default: bool = False`}
        </CodeBlock>

        <CodeBlock language="python" title="Output Structure">
{`# Returns:
{
    "enabled": True,
    "store": {"type": "memory"},
    "tokens": {
        "secret_key": "my-key",
        "algorithm": "HS256",
        "issuer": "aquilia",
        "audience": "aquilia-app",
        "access_token_ttl_minutes": 60,
        "refresh_token_ttl_days": 30,
    },
    "security": {
        "require_auth_by_default": False,
    }
}`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`# Simple:
.integrate(Integration.auth(secret_key="prod-secret"))

# Full AuthConfig:
.integrate(Integration.auth(config=AuthConfig(
    secret_key="prod-secret",
    algorithm="HS512",
    access_token_ttl_minutes=15,
    require_auth_by_default=True,
)))`}
        </CodeBlock>
      </section>

      {/* Database */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Database className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.database()
        </h2>

        <CodeBlock language="python" title="Signature">
{`@staticmethod
def database(
    url: str = "sqlite:///db.sqlite3",
    auto_connect: bool = True,
    auto_create: bool = True,
    auto_migrate: bool = False,
    migrations_dir: str = "migrations",
    pool_size: int = 5,
    echo: bool = False,
    model_paths: Optional[List[str]] = None,
    scan_dirs: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <div className={`overflow-x-auto mt-4 mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Parameter</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['url', '"sqlite:///db.sqlite3"', 'Database URL (sqlite, postgresql, mysql)'],
                ['auto_connect', 'True', 'Connect on server startup'],
                ['auto_create', 'True', 'Create tables from discovered AMDL models'],
                ['auto_migrate', 'False', 'Run pending migrations on startup'],
                ['migrations_dir', '"migrations"', 'Migration files directory'],
                ['pool_size', '5', 'Connection pool size'],
                ['echo', 'False', 'Log SQL statements to console'],
                ['model_paths', 'None → []', 'Explicit .amdl file paths'],
                ['scan_dirs', 'None → ["models"]', 'Directories to scan for .amdl files'],
              ].map(([param, def_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{param}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{def_}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" title="Usage">
{`# SQLite (development)
.integrate(Integration.database(url="sqlite:///app.db"))

# PostgreSQL (production)
.integrate(Integration.database(
    url="postgresql://user:pass@host:5432/mydb",
    pool_size=20,
    auto_migrate=True,
    scan_dirs=["models", "modules/*/models"],
))`}
        </CodeBlock>
      </section>

      {/* OpenAPI */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <FileText className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.openapi()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures OpenAPI 3.1.0 specification generation and interactive documentation
          (Swagger UI at <code>/docs</code>, ReDoc at <code>/redoc</code>).
        </p>

        <CodeBlock language="python" title="Key Parameters">
{`@staticmethod
def openapi(
    title: str = "Aquilia API",
    version: str = "1.0.0",
    description: str = "",
    terms_of_service: str = "",
    contact_name: str = "",
    contact_email: str = "",
    contact_url: str = "",
    license_name: str = "",
    license_url: str = "",
    servers: Optional[List[Dict[str, str]]] = None,
    docs_path: str = "/docs",
    openapi_json_path: str = "/openapi.json",
    redoc_path: str = "/redoc",
    include_internal: bool = False,
    group_by_module: bool = True,
    infer_request_body: bool = True,
    infer_responses: bool = True,
    detect_security: bool = True,
    external_docs_url: str = "",
    external_docs_description: str = "",
    swagger_ui_theme: str = "",        # "dark" for dark mode
    swagger_ui_config: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`.integrate(Integration.openapi(
    title="E-commerce API",
    version="2.0.0",
    description="Complete e-commerce platform API",
    contact_name="API Team",
    contact_email="api@company.com",
    license_name="MIT",
    servers=[
        {"url": "https://api.company.com", "description": "Production"},
        {"url": "https://staging-api.company.com", "description": "Staging"},
    ],
    swagger_ui_theme="dark",
    detect_security=True,
))`}
        </CodeBlock>
      </section>

      {/* Cache */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.cache()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures the caching subsystem. Supports memory (LRU/LFU), Redis, composite (L1+L2),
          and null backends with pluggable serialization and middleware.
        </p>

        <CodeBlock language="python" title="Key Parameters">
{`@staticmethod
def cache(
    backend: str = "memory",           # "memory", "redis", "composite", "null"
    default_ttl: int = 300,            # Default TTL in seconds
    max_size: int = 10000,             # Max entries for memory backend
    eviction_policy: str = "lru",      # "lru", "lfu", "fifo", "ttl", "random"
    namespace: str = "default",        # Namespace for key isolation
    key_prefix: str = "aq:",           # Global key prefix
    serializer: str = "json",          # "json", "pickle", "msgpack"
    redis_url: str = "redis://localhost:6379/0",
    redis_max_connections: int = 10,
    l1_max_size: int = 1000,           # L1 (memory) size for composite
    l1_ttl: int = 60,                  # L1 TTL for composite
    l2_backend: str = "redis",         # L2 backend for composite
    middleware_enabled: bool = False,   # HTTP response caching
    middleware_default_ttl: int = 60,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Backend Examples">
{`# Simple in-memory LRU cache (default)
.integrate(Integration.cache())

# Redis backend
.integrate(Integration.cache(
    backend="redis",
    redis_url="redis://cache-host:6379/0",
    default_ttl=600,
))

# Two-level composite cache (L1 memory + L2 Redis)
.integrate(Integration.cache(
    backend="composite",
    l1_max_size=500,
    l1_ttl=30,
    redis_url="redis://cache-host:6379/0",
))

# Null cache (disable caching, useful for testing)
.integrate(Integration.cache(backend="null"))`}
        </CodeBlock>
      </section>

      {/* Sessions */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Integration.sessions()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures session management with Aquilia's unique fluent policy builders.
          Provides smart defaults based on application type.
        </p>

        <CodeBlock language="python" title="Signature">
{`@staticmethod
def sessions(
    policy: Optional[Any] = None,     # SessionPolicy instance
    store: Optional[Any] = None,      # Store instance
    transport: Optional[Any] = None,  # Transport instance
    **kwargs
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Fluent Policy Builders">
{`from aquilia.sessions import SessionPolicy, MemoryStore, CookieTransport

# Full fluent syntax:
.integrate(Integration.sessions(
    policy=SessionPolicy.for_web_users()
        .lasting(days=14)
        .idle_timeout(hours=2)
        .rotating_on_privilege_change()
        .scoped_to("tenant"),
    store=MemoryStore.with_capacity(50000),
    transport=CookieTransport.secure_defaults(),
))`}
        </CodeBlock>

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Session Templates
        </h3>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>Integration.sessions</code> inner class provides pre-configured templates
          for common use cases:
        </p>

        <div className={`overflow-x-auto mb-6 rounded-xl border ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead className={isDark ? 'bg-gray-800/80' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Template</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>TTL</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Transport</th>
                <th className={`px-4 py-3 text-left font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Use Case</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-gray-700/50' : 'divide-gray-100'}`}>
              {[
                ['sessions.web_app()', '7 days', 'Cookie', 'Web applications with browser users'],
                ['sessions.api_service()', '1 hour', 'Header', 'REST APIs with token-based auth'],
                ['sessions.mobile_app()', '90 days', 'Cookie', 'Mobile apps with long-lived sessions'],
              ].map(([template, ttl, transport, useCase], i) => (
                <tr key={i} className={isDark ? 'hover:bg-gray-800/40' : 'hover:bg-gray-50/80'}>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-blue-600'}`}>{template}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{ttl}</td>
                  <td className={`px-4 py-3 font-mono text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{transport}</td>
                  <td className={`px-4 py-3 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{useCase}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <CodeBlock language="python" title="Template Usage">
{`# Pre-configured for web apps:
.integrate(Integration.sessions.web_app())

# Pre-configured for API services:
.integrate(Integration.sessions.api_service())

# Pre-configured for mobile apps:
.integrate(Integration.sessions.mobile_app())

# Templates accept overrides:
.integrate(Integration.sessions.web_app(idle_timeout_hours=4))`}
        </CodeBlock>
      </section>

      {/* CORS */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Globe className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.cors()
        </h2>

        <CodeBlock language="python" title="Signature">
{`@staticmethod
def cors(
    allow_origins: Optional[List[str]] = None,        # Default: ["*"]
    allow_methods: Optional[List[str]] = None,        # Default: all methods
    allow_headers: Optional[List[str]] = None,        # Default: common headers
    expose_headers: Optional[List[str]] = None,       # Default: []
    allow_credentials: bool = False,
    max_age: int = 600,                               # Preflight cache (seconds)
    allow_origin_regex: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`# Development (allow everything):
.integrate(Integration.cors())

# Production (restricted):
.integrate(Integration.cors(
    allow_origins=["https://myapp.com", "*.staging.myapp.com"],
    allow_credentials=True,
    max_age=3600,
))`}
        </CodeBlock>
      </section>

      {/* CSRF */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.csrf()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures CSRF protection middleware with double-submit cookie pattern.
        </p>

        <CodeBlock language="python" title="Key Parameters">
{`@staticmethod
def csrf(
    secret_key: str = "",
    token_length: int = 32,
    header_name: str = "X-CSRF-Token",
    field_name: str = "_csrf_token",
    cookie_name: str = "_csrf_cookie",
    cookie_path: str = "/",
    cookie_domain: Optional[str] = None,
    cookie_secure: bool = True,
    cookie_samesite: str = "Lax",      # "Strict", "Lax", "None"
    cookie_httponly: bool = False,
    cookie_max_age: int = 3600,
    safe_methods: Optional[List[str]] = None,  # Default: GET, HEAD, OPTIONS, TRACE
    exempt_paths: Optional[List[str]] = None,
    exempt_content_types: Optional[List[str]] = None,
    trust_ajax: bool = True,            # Trust X-Requested-With header
    rotate_token: bool = False,         # New token after each validation
    failure_status: int = 403,
    enabled: bool = True,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`.integrate(Integration.csrf(
    secret_key="csrf-secret-key",
    exempt_paths=["/api/webhooks", "/health"],
    cookie_secure=True,
    cookie_samesite="Strict",
))`}
        </CodeBlock>
      </section>

      {/* CSP */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Integration.csp()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures Content-Security-Policy middleware with per-request nonce generation.
        </p>

        <CodeBlock language="python" title="Signature &amp; Usage">
{`@staticmethod
def csp(
    policy: Optional[Dict[str, List[str]]] = None,
    report_only: bool = False,
    nonce: bool = True,           # Enable per-request nonce
    preset: str = "strict",       # "strict" or "relaxed" (when policy is None)
    **kwargs,
) -> Dict[str, Any]:

# Usage:
.integrate(Integration.csp(
    policy={
        "default-src": ["'self'"],
        "script-src": ["'self'", "'nonce-{nonce}'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "https:"],
    },
    nonce=True,
))`}
        </CodeBlock>
      </section>

      {/* Rate Limit */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Integration.rate_limit()
        </h2>

        <CodeBlock language="python" title="Signature">
{`@staticmethod
def rate_limit(
    limit: int = 100,                          # Max requests per window
    window: int = 60,                          # Window size (seconds)
    algorithm: str = "sliding_window",         # "sliding_window" or "token_bucket"
    per_user: bool = False,                    # Key by user identity (requires auth)
    burst: Optional[int] = None,              # Extra burst capacity (token_bucket)
    exempt_paths: Optional[List[str]] = None,  # Default: /health, /healthz, /ready
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`# Default: 100 requests/minute, sliding window
.integrate(Integration.rate_limit())

# Token bucket with burst:
.integrate(Integration.rate_limit(
    limit=200,
    window=60,
    algorithm="token_bucket",
    burst=50,
    per_user=True,
))`}
        </CodeBlock>
      </section>

      {/* Static Files */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Integration.static_files()
        </h2>

        <CodeBlock language="python" title="Signature">
{`@staticmethod
def static_files(
    directories: Optional[Dict[str, str]] = None,  # {url_prefix: fs_dir}
    cache_max_age: int = 86400,                     # 1 day
    immutable: bool = False,                        # For fingerprinted assets
    etag: bool = True,
    gzip: bool = True,                              # Serve .gz files
    brotli: bool = True,                            # Serve .br files
    memory_cache: bool = True,                      # In-memory LRU file cache
    html5_history: bool = False,                    # SPA fallback to index.html
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`.integrate(Integration.static_files(
    directories={
        "/static": "static",
        "/media": "uploads",
        "/assets": "dist/assets",
    },
    cache_max_age=86400,
    etag=True,
    html5_history=True,  # SPA mode
))`}
        </CodeBlock>
      </section>

      {/* Templates */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layout className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.templates
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Unlike other integrations, <code>templates</code> uses a fluent builder pattern
          via an inner <code>Builder</code> class that inherits from <code>dict</code> for
          compatibility with the integration pipeline.
        </p>

        <CodeBlock language="python" title="Fluent Builder API">
{`# Start with source paths:
Integration.templates.source("templates", "shared_templates")

# Chainable methods:
.source(*paths)       # Add template search paths
.scan_modules()       # Enable module auto-discovery
.cached(strategy)     # Enable bytecode caching ("memory" default)
.secure(strict)       # Enable sandbox with security policy
.unsafe_dev_mode()    # Disable sandbox + caching (development)
.precompile()         # Enable startup precompilation

# Start with defaults:
Integration.templates.defaults()`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage Examples">
{`# Production: cached, sandboxed, precompiled
.integrate(
    Integration.templates
        .source("templates")
        .cached("memory")
        .secure(strict=True)
        .precompile()
)

# Development: no sandbox, no caching
.integrate(
    Integration.templates
        .source("templates", "components")
        .unsafe_dev_mode()
)

# Defaults (source="templates", cache="memory", sandbox=True)
.integrate(Integration.templates.defaults())`}
        </CodeBlock>
      </section>

      {/* Logging */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Eye className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.logging()
        </h2>

        <CodeBlock language="python" title="Signature">
{`@staticmethod
def logging(
    format: str = "%(method)s %(path)s %(status)s %(duration_ms).1fms",
    level: str = "INFO",
    slow_threshold_ms: float = 1000.0,    # Flag requests above this
    skip_paths: Optional[List[str]] = None,  # Default: /health, /healthz, /ready, /metrics
    include_headers: bool = False,
    include_query: bool = True,
    include_user_agent: bool = False,
    log_request_body: bool = False,       # Use with caution
    log_response_body: bool = False,      # Use with caution
    colorize: bool = True,               # Color output (development)
    enabled: bool = True,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`.integrate(Integration.logging(
    slow_threshold_ms=500,
    skip_paths=["/health", "/metrics"],
    include_headers=True,
    colorize=False,  # Disable for production log aggregators
))`}
        </CodeBlock>
      </section>

      {/* Mail */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Mail className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.mail()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures AquilaMail — the production-ready async mail subsystem with retry,
          rate limiting, DKIM signing, and template rendering.
        </p>

        <CodeBlock language="python" title="Key Parameters">
{`@staticmethod
def mail(
    default_from: str = "noreply@localhost",
    default_reply_to: Optional[str] = None,
    subject_prefix: str = "",
    providers: Optional[List[Dict[str, Any]]] = None,
    console_backend: bool = False,       # Print to console (development)
    preview_mode: bool = False,          # Render only, no delivery
    template_dirs: Optional[List[str]] = None,  # Default: ["mail_templates"]
    retry_max_attempts: int = 5,
    retry_base_delay: float = 1.0,       # Exponential backoff base
    rate_limit_global: int = 1000,       # Messages/minute
    rate_limit_per_domain: int = 100,
    dkim_enabled: bool = False,
    dkim_domain: Optional[str] = None,
    dkim_selector: str = "aquilia",
    require_tls: bool = True,
    pii_redaction: bool = False,
    metrics_enabled: bool = True,
    tracing_enabled: bool = False,
    enabled: bool = True,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`# Development (console output):
.integrate(Integration.mail(console_backend=True))

# Production (SMTP with DKIM):
.integrate(Integration.mail(
    default_from="noreply@myapp.com",
    providers=[
        {"name": "primary", "type": "smtp", "host": "smtp.ses.amazonaws.com", "port": 587},
        {"name": "fallback", "type": "smtp", "host": "smtp.mailgun.org", "port": 587},
    ],
    dkim_enabled=True,
    dkim_domain="myapp.com",
    retry_max_attempts=3,
    rate_limit_global=500,
    pii_redaction=True,
))`}
        </CodeBlock>
      </section>

      {/* MLOps */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Cpu className="w-5 h-5 inline mr-2 text-aquilia-400" />
          Integration.mlops()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures the MLOps platform — model packaging, registry, serving, observability,
          release management, scheduling, security, and plugin system. Integrates with
          CacheService, FaultEngine, ArtifactStore, and Effects.
        </p>

        <CodeBlock language="python" title="Key Parameters">
{`@staticmethod
def mlops(
    *,
    enabled: bool = True,
    registry_db: str = "registry.db",           # Registry SQLite database
    blob_root: str = ".aquilia-store",           # Blob storage root
    storage_backend: str = "filesystem",         # "filesystem" or "s3"
    drift_method: str = "psi",                   # "psi", "ks_test", "distribution"
    drift_threshold: float = 0.2,
    drift_num_bins: int = 10,
    max_batch_size: int = 16,                    # Dynamic batcher
    max_latency_ms: float = 50.0,
    batching_strategy: str = "hybrid",           # "size", "time", "hybrid"
    sample_rate: float = 0.01,                   # Prediction logging
    log_dir: str = "prediction_logs",
    hmac_secret: Optional[str] = None,           # Artifact signing
    signing_private_key: Optional[str] = None,
    signing_public_key: Optional[str] = None,
    encryption_key: Optional[Any] = None,        # Blob encryption
    plugin_auto_discover: bool = True,
    scaling_policy: Optional[Dict[str, Any]] = None,
    rollout_default_strategy: str = "canary",
    auto_rollback: bool = True,
    cache_enabled: bool = True,                  # CacheService integration
    cache_ttl: int = 60,
    cache_namespace: str = "mlops",
    artifact_store_dir: str = "artifacts",
    fault_engine_debug: bool = False,
    **kwargs,
) -> Dict[str, Any]:`}
        </CodeBlock>

        <CodeBlock language="python" title="Output Structure">
{`# Returns nested dict:
{
    "_integration_type": "mlops",
    "enabled": True,
    "registry": {"db_path": "...", "blob_root": "...", "storage_backend": "..."},
    "serving":  {"max_batch_size": 16, "max_latency_ms": 50.0, "batching_strategy": "..."},
    "observe":  {"drift_method": "...", "drift_threshold": 0.2, ...},
    "release":  {"rollout_default_strategy": "canary", "auto_rollback": True},
    "security": {"hmac_secret": None, ...},
    "plugins":  {"auto_discover": True},
    "scaling_policy": None,
    "ecosystem": {"cache_enabled": True, "cache_ttl": 60, ...},
}`}
        </CodeBlock>

        <CodeBlock language="python" title="Usage">
{`.integrate(Integration.mlops(
    registry_db="models.db",
    drift_method="psi",
    drift_threshold=0.25,
    max_batch_size=32,
    plugin_auto_discover=True,
    cache_enabled=True,
    cache_ttl=120,
))`}
        </CodeBlock>
      </section>

      {/* Serializers */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Integration.serializers()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configures global serializer settings for validation, formatting, and error handling.
        </p>

        <CodeBlock language="python" title="Signature &amp; Usage">
{`@staticmethod
def serializers(
    *,
    auto_discover: bool = True,
    strict_validation: bool = True,        # Reject unknown fields
    raise_on_error: bool = False,          # Raise ValidationFault vs return errors
    date_format: str = "iso-8601",
    datetime_format: str = "iso-8601",
    coerce_decimal_to_string: bool = True,
    compact_json: bool = True,             # No indent in JSON output
    enabled: bool = True,
    **kwargs,
) -> Dict[str, Any]:

# Usage:
.integrate(Integration.serializers(
    strict_validation=True,
    raise_on_error=True,
    coerce_decimal_to_string=False,
))`}
        </CodeBlock>
      </section>

      {/* Simple Integrations */}
      <section className="mb-12">
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Simple Integrations
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          These integrations have minimal configuration:
        </p>

        <CodeBlock language="python" title="Simple Integration Methods">
{`# Dependency injection
Integration.di(auto_wire=True, **kwargs)
# → {"enabled": True, "auto_wire": True}

# Routing
Integration.routing(strict_matching=True, **kwargs)
# → {"enabled": True, "strict_matching": True}

# Fault handling
Integration.fault_handling(default_strategy="propagate", **kwargs)
# → {"enabled": True, "default_strategy": "propagate"}

# Registry
Integration.registry(**kwargs)
# → {"enabled": True}

# Patterns
Integration.patterns(**kwargs)
# → {"enabled": True}`}
        </CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`mt-12 pt-6 border-t flex justify-between ${isDark ? 'border-gray-700/50' : 'border-gray-200'}`}>
        <Link
          to="/docs/config/module"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          ← Module Builder
        </Link>
        <Link
          to="/docs/request-response/request"
          className="flex items-center gap-2 text-aquilia-400 hover:text-aquilia-300 transition-colors"
        >
          Request &amp; Response <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    
      <NextSteps />
    </div>
  )
}