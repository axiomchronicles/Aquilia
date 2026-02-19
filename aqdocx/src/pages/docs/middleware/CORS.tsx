import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Layers } from 'lucide-react'

export function MiddlewareCORS() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Layers className="w-4 h-4" />
          Middleware / CORS
        </div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            CORSMiddleware
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Cross-Origin Resource Sharing middleware. Handles preflight OPTIONS requests and sets the appropriate CORS headers on responses.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration</h2>
        <CodeBlock language="python" filename="cors.py">{`from aquilia.middleware_ext import CORSMiddleware

cors = CORSMiddleware(
    allow_origins=["https://example.com", "https://app.example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    allow_credentials=True,
    max_age=3600,           # Preflight cache duration
)

# Wildcard (development only!)
cors = CORSMiddleware(allow_origins=["*"])

# Regex patterns
cors = CORSMiddleware(
    allow_origin_regex=r"https://.*\\.example\\.com",
)`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Options Reference</h2>
        <div className="overflow-x-auto">
          <table className={`w-full text-sm border-collapse ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <thead>
              <tr className={isDark ? 'border-b border-white/10' : 'border-b border-gray-200'}>
                <th className="py-3 px-4 text-left font-semibold">Option</th>
                <th className="py-3 px-4 text-left font-semibold">Type</th>
                <th className="py-3 px-4 text-left font-semibold">Default</th>
                <th className="py-3 px-4 text-left font-semibold">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['allow_origins', 'list[str]', '[]', 'Allowed origin URLs'],
                ['allow_origin_regex', 'str | None', 'None', 'Regex pattern for origins'],
                ['allow_methods', 'list[str]', '["GET"]', 'Allowed HTTP methods'],
                ['allow_headers', 'list[str]', '[]', 'Allowed request headers'],
                ['expose_headers', 'list[str]', '[]', 'Headers exposed to browser'],
                ['allow_credentials', 'bool', 'False', 'Allow cookies/auth headers'],
                ['max_age', 'int', '600', 'Preflight cache in seconds'],
              ].map(([opt, type, def_, desc], i) => (
                <tr key={i} className={isDark ? 'border-b border-white/5' : 'border-b border-gray-100'}>
                  <td className="py-2.5 px-4 font-mono text-aquilia-400 text-xs">{opt}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{type}</td>
                  <td className="py-2.5 px-4 font-mono text-xs">{def_}</td>
                  <td className="py-2.5 px-4 text-xs">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
