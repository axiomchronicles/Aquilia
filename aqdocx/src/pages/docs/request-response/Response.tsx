import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { ArrowUpFromLine } from 'lucide-react'

export function ResponsePage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><ArrowUpFromLine className="w-4 h-4" />Core</div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response</h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">Response</code> class provides factory methods for JSON, HTML, file streaming, SSE, redirects, and more. It handles content negotiation, compression, cookie setting, and CORS headers.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Factory Methods</h2>
        <CodeBlock language="python" filename="Response Types">{`from aquilia.response import Response

# JSON response (most common)
return Response.json({"message": "Hello"}, status=200)

# HTML response
return Response.html("<h1>Hello</h1>", status=200)

# Plain text
return Response.text("OK", status=200)

# Redirect
return Response.redirect("/login", status=302)  # or 301

# File download
return Response.file("path/to/report.pdf", filename="report.pdf")

# Streaming response
async def generate():
    for i in range(100):
        yield f"data: {i}\\n\\n"
        await asyncio.sleep(0.1)

return Response.stream(generate(), content_type="text/event-stream")

# Server-Sent Events (SSE)
async def events():
    while True:
        data = await get_latest_data()
        yield {"event": "update", "data": json.dumps(data)}
        await asyncio.sleep(1)

return Response.sse(events())

# Template rendering (via controller.render())
return await self.render("page.html", {"title": "Home"}, ctx)

# Empty response (204 No Content)
return Response.empty(status=204)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Headers & Cookies</h2>
        <CodeBlock language="python" filename="Headers & Cookies">{`# Set custom headers
response = Response.json({"ok": True})
response.headers["X-Custom-Header"] = "value"
response.headers["Cache-Control"] = "no-store"

# Set cookies
response.set_cookie(
    key="session_id",
    value="abc123",
    max_age=3600,       # 1 hour
    httponly=True,       # Not accessible via JavaScript
    secure=True,         # HTTPS only
    samesite="Lax",     # CSRF protection
    path="/",
    domain=".example.com",
)

# Delete cookies
response.delete_cookie("session_id")

# Set multiple headers at once
response = Response.json(
    {"data": "value"},
    headers={
        "X-RateLimit-Remaining": "99",
        "X-RateLimit-Reset": "1640000000",
    }
)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Compression</h2>
        <div className={`p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`}>
          <p className={`${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            Aquilia automatically compresses responses when the client sends an <code className="text-aquilia-500">Accept-Encoding</code> header. Supported algorithms:
          </p>
          <ul className={`space-y-2 mt-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span><strong>gzip</strong> — Standard gzip compression</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span><strong>br</strong> — Brotli compression (higher ratio)</li>
            <li className="flex gap-2"><span className="text-aquilia-500">•</span><strong>deflate</strong> — Deflate compression</li>
          </ul>
          <p className={`mt-3 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
            Compression is skipped for small responses ({'<'}1KB), streaming responses, and already-compressed content types (images, video).
          </p>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using in Controllers</h2>
        <CodeBlock language="python" filename="Controller Response Patterns">{`class APIController(Controller):
    prefix = "/api"

    @Get("/data")
    async def get_data(self, ctx):
        # Via ctx (shortcut — creates Response internally)
        return ctx.json({"key": "value"})

    @Get("/page")
    async def page(self, ctx):
        # Via Response class directly
        return Response.html("<h1>Page</h1>")

    @Get("/download")
    async def download(self, ctx):
        return Response.file(
            "reports/monthly.csv",
            filename="report.csv",
            content_type="text/csv"
        )

    @Get("/events")
    async def events(self, ctx):
        async def stream():
            for i in range(10):
                yield {"event": "tick", "data": str(i)}
                await asyncio.sleep(1)
        return Response.sse(stream())`}</CodeBlock>
      </section>
    </div>
  )
}
