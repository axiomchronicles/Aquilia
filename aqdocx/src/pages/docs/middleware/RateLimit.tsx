import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Layers } from 'lucide-react'

export function MiddlewareRateLimit() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Layers className="w-4 h-4" />
          Middleware / Rate Limiting
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            RateLimitMiddleware
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Token-bucket rate limiting with per-route, per-user, and global rules. Returns <code className="text-aquilia-400">429 Too Many Requests</code> with <code className="text-aquilia-400">Retry-After</code> header.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="ratelimit.py">{`from aquilia.middleware_ext import RateLimitMiddleware, RateLimitRule

limiter = RateLimitMiddleware(
    rules=[
        # Global: 100 requests per minute
        RateLimitRule(
            requests=100,
            window=60,
            scope="global",
        ),
        
        # Per-user: 30 requests per minute
        RateLimitRule(
            requests=30,
            window=60,
            scope="user",
            key=lambda req: req.user.id if req.user else req.client.host,
        ),
        
        # Per-route: 5 login attempts per 5 minutes
        RateLimitRule(
            requests=5,
            window=300,
            scope="route",
            routes=["/auth/login"],
        ),
    ],
    storage="memory",  # or "redis://localhost:6379"
)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>RateLimitRule Options</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Option</th>
                <th className="py-3 px-4 text-left font-semibold">Type</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['requests', 'int', 'Maximum requests in window'],
                ['window', 'int', 'Window size in seconds'],
                ['scope', 'str', '"global", "user", or "route"'],
                ['key', 'Callable', 'Function to extract rate limit key'],
                ['routes', 'list[str] | None', 'Specific routes to limit'],
                ['methods', 'list[str] | None', 'HTTP methods to limit'],
                ['exempt', 'list[str] | None', 'Routes exempt from this rule'],
                ['burst', 'int | None', 'Allow burst above limit temporarily'],
              ].map(([opt, type, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{opt}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{type}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Response Headers</h2>
        <CodeBlock language="python" filename="headers.py">{`# Rate limit headers added to every response:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 73
# X-RateLimit-Reset: 1705312800

# On 429 response:
# Retry-After: 42`}</CodeBlock>
      </section>
    </div>
  )
}
