import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Shield } from 'lucide-react'

export function MiddlewareExtended() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Shield className="w-4 h-4" />
          Middleware / Extended
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            CORS, Rate Limiting, Static Files & Security
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia ships with production-grade middleware extensions for cross-origin requests, rate limiting, static file serving, CSRF protection, and security headers.
        </p>
      </div>

      {/* CORS */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CORSMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Full RFC 6454/7231 compliant CORS with regex and glob origin matching, preflight caching, and credential support.
        </p>
        <CodeBlock language="python" filename="cors.py">{`from aquilia.middleware_ext import CORSMiddleware

app.add_middleware(CORSMiddleware(
    allow_origins=[
        "https://app.example.com",
        "https://*.example.com",      # Glob pattern
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    allow_credentials=True,
    max_age=3600,                     # Preflight cache (seconds)
))`}</CodeBlock>
      </section>

      {/* Rate Limiting */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RateLimitMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Token bucket and sliding window rate limiting with configurable rules, key extractors, and response headers.
        </p>
        <CodeBlock language="python" filename="rate_limit.py">{`from aquilia.middleware_ext import (
    RateLimitMiddleware,
    RateLimitRule,
    ip_key_extractor,
    api_key_extractor,
    user_key_extractor,
)

app.add_middleware(RateLimitMiddleware(
    rules=[
        # 100 requests per minute per IP (global)
        RateLimitRule(
            max_requests=100,
            window_seconds=60,
            key_extractor=ip_key_extractor,
        ),

        # 1000 requests per hour per API key
        RateLimitRule(
            max_requests=1000,
            window_seconds=3600,
            key_extractor=api_key_extractor,
            path_pattern="/api/*",
        ),

        # 10 login attempts per 5 minutes per IP
        RateLimitRule(
            max_requests=10,
            window_seconds=300,
            key_extractor=ip_key_extractor,
            path_pattern="/auth/login",
            methods=["POST"],
        ),
    ],
))

# Response headers added automatically:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 95
# X-RateLimit-Reset: 1700000060
# Retry-After: 42  (when rate limited → 429 Too Many Requests)`}</CodeBlock>
      </section>

      {/* Static Files */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>StaticMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Production-grade static file serving with radix trie path matching, ETag support, range requests, and automatic content-type detection.
        </p>
        <CodeBlock language="python" filename="static.py">{`from aquilia.middleware_ext import StaticMiddleware

app.add_middleware(StaticMiddleware(
    directory="static",            # Relative to project root
    prefix="/static",              # URL prefix
    max_age=86400,                 # Cache-Control max-age (seconds)
    etag=True,                     # ETag generation for caching
    gzip=True,                     # Serve .gz files when available
    index_file="index.html",       # Serve for directory requests
    fallback=None,                 # Fallback file for SPA routing
))

# Serves: /static/css/main.css → static/css/main.css
# Serves: /static/js/app.js → static/js/app.js
# Headers: Cache-Control, ETag, Content-Type, Accept-Ranges`}</CodeBlock>
      </section>

      {/* CSRF */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CSRFMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          CSRF protection using Synchronizer Token pattern + Double Submit Cookie. Automatically generates and validates tokens.
        </p>
        <CodeBlock language="python" filename="csrf.py">{`from aquilia.middleware_ext import CSRFMiddleware, csrf_exempt

app.add_middleware(CSRFMiddleware(
    cookie_name="csrftoken",
    header_name="X-CSRFToken",
    safe_methods=["GET", "HEAD", "OPTIONS"],
    cookie_secure=True,
    cookie_httponly=True,
    cookie_samesite="Lax",
))


# Exempt specific routes
class WebhookController(Controller):
    prefix = "/webhooks"

    @Post("/stripe")
    @csrf_exempt
    async def stripe_webhook(self, ctx):
        """Webhooks are exempt from CSRF protection."""
        ...


# In templates (auto-injected)
# <form method="POST">
#   <input type="hidden" name="csrftoken" value="{{ csrf_token }}">
#   ...
# </form>`}</CodeBlock>
      </section>

      {/* Security Headers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SecurityHeadersMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Helmet-style catch-all security headers middleware. Combines CSP, HSTS, and other hardening headers.
        </p>
        <CodeBlock language="python" filename="security_headers.py">{`from aquilia.middleware_ext import (
    SecurityHeadersMiddleware,
    CSPMiddleware,
    CSPPolicy,
    HSTSMiddleware,
    HTTPSRedirectMiddleware,
    ProxyFixMiddleware,
)

# All-in-one security headers
app.add_middleware(SecurityHeadersMiddleware(
    csp=CSPPolicy(
        default_src=["'self'"],
        script_src=["'self'", "'nonce-{nonce}'"],
        style_src=["'self'", "'unsafe-inline'"],
        img_src=["'self'", "data:", "https:"],
        connect_src=["'self'", "wss:"],
        frame_ancestors=["'none'"],
    ),
    hsts_max_age=31536000,          # 1 year
    hsts_include_subdomains=True,
    hsts_preload=True,
    x_content_type_options="nosniff",
    x_frame_options="DENY",
    x_xss_protection="1; mode=block",
    referrer_policy="strict-origin-when-cross-origin",
    permissions_policy={
        "camera": "()",
        "microphone": "()",
        "geolocation": "(self)",
    },
))

# Or use individual middleware
app.add_middleware(HSTSMiddleware(max_age=31536000))
app.add_middleware(HTTPSRedirectMiddleware(
    exempt_paths=["/health", "/.well-known"],
))
app.add_middleware(ProxyFixMiddleware(
    trusted_proxies=["10.0.0.0/8"],
    trust_x_forwarded_for=True,
    trust_x_forwarded_proto=True,
))`}</CodeBlock>
      </section>

      {/* Logging */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>LoggingMiddleware</h2>
        <CodeBlock language="python" filename="logging_mw.py">{`from aquilia.middleware_ext import (
    EnhancedLoggingMiddleware,
    CombinedLogFormatter,
    StructuredLogFormatter,
    DevLogFormatter,
)

# Development mode — colorful, readable
app.add_middleware(EnhancedLoggingMiddleware(
    formatter=DevLogFormatter(),
))
# → GET /api/users 200 12ms

# Production — structured JSON
app.add_middleware(EnhancedLoggingMiddleware(
    formatter=StructuredLogFormatter(),
))
# → {"method":"GET","path":"/api/users","status":200,"duration_ms":12,...}

# Apache Combined Log Format
app.add_middleware(EnhancedLoggingMiddleware(
    formatter=CombinedLogFormatter(),
))
# → 127.0.0.1 - - [01/Jan/2025:00:00:00 +0000] "GET /api/users HTTP/1.1" 200 1234`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/middleware/built-in" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Built-in Middleware
        </Link>
        <Link to="/docs/faults" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          Faults <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
