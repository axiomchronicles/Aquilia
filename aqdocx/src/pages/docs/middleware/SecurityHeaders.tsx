import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Layers } from 'lucide-react'

export function MiddlewareSecurityHeaders() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Layers className="w-4 h-4" />
          Middleware / Security Headers
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Security Headers Middleware
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          A collection of middleware for CSP, CSRF, HSTS, and general security headers. Each can be used independently or combined via <code className="text-aquilia-400">SecurityHeadersMiddleware</code>.
        </p>
      </div>

      {/* SecurityHeadersMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>SecurityHeadersMiddleware</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Combines all security headers in one middleware. Adds sensible defaults for production.
        </p>
        <CodeBlock language="python" filename="security.py">{`from aquilia.middleware_ext import SecurityHeadersMiddleware

security = SecurityHeadersMiddleware(
    x_content_type_options="nosniff",
    x_frame_options="DENY",
    x_xss_protection="1; mode=block",
    referrer_policy="strict-origin-when-cross-origin",
    permissions_policy="camera=(), microphone=(), geolocation=()",
)`}</CodeBlock>
      </section>

      {/* CSPMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CSPMiddleware</h2>
        <CodeBlock language="python" filename="csp.py">{`from aquilia.middleware_ext import CSPMiddleware

csp = CSPMiddleware(
    default_src=["'self'"],
    script_src=["'self'", "https://cdn.example.com"],
    style_src=["'self'", "'unsafe-inline'"],
    img_src=["'self'", "data:", "https:"],
    font_src=["'self'", "https://fonts.gstatic.com"],
    connect_src=["'self'", "https://api.example.com"],
    frame_ancestors=["'none'"],
    report_uri="/csp-report",
    report_only=False,  # True for testing
)`}</CodeBlock>
      </section>

      {/* CSRFMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>CSRFMiddleware</h2>
        <CodeBlock language="python" filename="csrf.py">{`from aquilia.middleware_ext import CSRFMiddleware

csrf = CSRFMiddleware(
    cookie_name="csrf_token",
    header_name="X-CSRF-Token",
    safe_methods=["GET", "HEAD", "OPTIONS"],
    cookie_secure=True,
    cookie_httponly=True,
    cookie_samesite="lax",
    exempt_routes=["/api/webhooks/"],  # Skip for webhooks
)`}</CodeBlock>
      </section>

      {/* HSTSMiddleware */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>HSTSMiddleware</h2>
        <CodeBlock language="python" filename="hsts.py">{`from aquilia.middleware_ext import HSTSMiddleware

hsts = HSTSMiddleware(
    max_age=31536000,              # 1 year
    include_subdomains=True,
    preload=True,                  # Submit to HSTS preload list
)`}</CodeBlock>
      </section>

      {/* Headers Table */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Headers Added</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Header</th>
                <th className="py-3 px-4 text-left font-semibold">Middleware</th>
                <th className="py-3 px-4 text-left font-semibold">Default Value</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Content-Security-Policy', 'CSP', "default-src 'self'"],
                ['Strict-Transport-Security', 'HSTS', 'max-age=31536000'],
                ['X-Content-Type-Options', 'Security', 'nosniff'],
                ['X-Frame-Options', 'Security', 'DENY'],
                ['X-XSS-Protection', 'Security', '1; mode=block'],
                ['Referrer-Policy', 'Security', 'strict-origin-when-cross-origin'],
                ['Permissions-Policy', 'Security', 'camera=(), microphone=()'],
              ].map(([header, mw, value], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{header}</td>
                  <td className="py-2.5 px-4 text-xs">{mw}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
