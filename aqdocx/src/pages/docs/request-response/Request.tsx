import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { ArrowDownToLine } from 'lucide-react'

export function RequestPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><ArrowDownToLine className="w-4 h-4" />Core</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Request</code> class is a production-grade HTTP request wrapper built on the ASGI scope. It provides async body parsing, streaming, multipart uploads, cookie handling, security headers, and content negotiation.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Key Properties</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead><tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Property</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
              <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
            </tr></thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { p: 'method', t: 'str', d: 'HTTP method (GET, POST, PUT, DELETE, etc.)' },
                { p: 'path', t: 'str', d: 'URL path (e.g., "/api/users/42")' },
                { p: 'url', t: 'str', d: 'Full URL including scheme, host, path, and query' },
                { p: 'headers', t: 'Dict[str, str]', d: 'Request headers (case-insensitive keys)' },
                { p: 'query_params', t: 'Dict[str, list]', d: 'Parsed query string parameters' },
                { p: 'cookies', t: 'Dict[str, str]', d: 'Parsed cookies from the Cookie header' },
                { p: 'content_type', t: 'str | None', d: 'Content-Type header value' },
                { p: 'client', t: 'tuple', d: 'Client address (host, port)' },
                { p: 'scheme', t: 'str', d: '"http" or "https"' },
                { p: 'is_secure', t: 'bool', d: 'Whether the request is over HTTPS' },
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

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Async Body Methods</h2>
        <CodeBlock language="python" filename="Body Parsing">{`# JSON body
body = await request.json()

# Form data (application/x-www-form-urlencoded)
form = await request.form()

# Raw bytes
raw = await request.body()

# Text
text = await request.text()

# Multipart form data (file uploads)
multipart = await request.multipart()
file = multipart.get("avatar")
if file:
    content = await file.read()
    filename = file.filename
    content_type = file.content_type

# Streaming body (for large uploads)
async for chunk in request.stream():
    process(chunk)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Query Parameters</h2>
        <CodeBlock language="python" filename="Query Params">{`# GET /search?q=python&page=2&tags=web&tags=api

# Get all values for a key (returns list)
tags = request.query_params.get("tags")  # ["web", "api"]

# Get single value (convenience method)
query = request.query_param("q")          # "python"
page = request.query_param("page", "1")   # "2"
missing = request.query_param("x", "def") # "def"`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Headers & Cookies</h2>
        <CodeBlock language="python" filename="Headers & Cookies">{`# Headers (case-insensitive)
auth = request.headers.get("authorization")
ct = request.headers.get("content-type")
ua = request.headers.get("user-agent")

# Cookies
session_id = request.cookies.get("session_id")
theme = request.cookies.get("theme", "dark")

# Check for specific header
if request.headers.get("x-requested-with") == "XMLHttpRequest":
    # AJAX request
    ...`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Security Features</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <ul className={`space-y-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>Request body size limits to prevent DOS</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>Content-Type validation and enforcement</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>Header injection prevention</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>Path traversal protection</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span>IP address extraction with proxy support (X-Forwarded-For)</li>
          </ul>
        </div>
      </section>
    </div>
  )
}
