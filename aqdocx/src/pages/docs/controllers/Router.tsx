import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { GitBranch, ArrowLeft, ArrowRight } from 'lucide-react'

export function ControllersRouter() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <GitBranch className="w-4 h-4" />
          Core / Controllers / Router
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Controller Router
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ControllerRouter</code> is a pattern-based URL router that matches incoming HTTP requests to compiled controller routes. It uses Aquilia's built-in pattern matching engine with typed parameters, specificity-based resolution, and reverse URL generation.
        </p>
      </div>

      {/* Architecture SVG */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>How Routing Works</h2>
        <div className={boxClass}>
          <svg viewBox="0 0 700 200" className="w-full" fill="none">
            <rect x="10" y="60" width="120" height="60" rx="10" stroke={isDark ? '#22c55e' : '#16a34a'} strokeWidth="2" fill={isDark ? '#22c55e10' : '#16a34a08'} />
            <text x="70" y="95" textAnchor="middle" fill={isDark ? '#4ade80' : '#16a34a'} fontSize="13" fontWeight="bold">HTTP Request</text>
            <path d="M130 90 L180 90" stroke={isDark ? '#4ade80' : '#16a34a'} strokeWidth="2" markerEnd="url(#arrowG)" />
            <rect x="180" y="60" width="130" height="60" rx="10" stroke={isDark ? '#60a5fa' : '#2563eb'} strokeWidth="2" fill={isDark ? '#60a5fa10' : '#2563eb08'} />
            <text x="245" y="88" textAnchor="middle" fill={isDark ? '#93c5fd' : '#2563eb'} fontSize="12" fontWeight="bold">ControllerRouter</text>
            <text x="245" y="103" textAnchor="middle" fill={isDark ? '#6b7280' : '#94a3b8'} fontSize="10">.match(path, method)</text>
            <path d="M310 90 L360 90" stroke={isDark ? '#60a5fa' : '#2563eb'} strokeWidth="2" markerEnd="url(#arrowB)" />
            <rect x="360" y="60" width="130" height="60" rx="10" stroke={isDark ? '#fbbf24' : '#d97706'} strokeWidth="2" fill={isDark ? '#fbbf2410' : '#d9770608'} />
            <text x="425" y="88" textAnchor="middle" fill={isDark ? '#fde047' : '#d97706'} fontSize="12" fontWeight="bold">PatternMatcher</text>
            <text x="425" y="103" textAnchor="middle" fill={isDark ? '#6b7280' : '#94a3b8'} fontSize="10">specificity sort</text>
            <path d="M490 90 L540 90" stroke={isDark ? '#fbbf24' : '#d97706'} strokeWidth="2" markerEnd="url(#arrowY)" />
            <rect x="540" y="60" width="140" height="60" rx="10" stroke={isDark ? '#a78bfa' : '#7c3aed'} strokeWidth="2" fill={isDark ? '#a78bfa10' : '#7c3aed08'} />
            <text x="610" y="88" textAnchor="middle" fill={isDark ? '#c4b5fd' : '#7c3aed'} fontSize="12" fontWeight="bold">CompiledRoute</text>
            <text x="610" y="103" textAnchor="middle" fill={isDark ? '#6b7280' : '#94a3b8'} fontSize="10">params + handler</text>
            <defs>
              <marker id="arrowG" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill={isDark ? '#4ade80' : '#16a34a'} /></marker>
              <marker id="arrowB" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill={isDark ? '#60a5fa' : '#2563eb'} /></marker>
              <marker id="arrowY" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill={isDark ? '#fbbf24' : '#d97706'} /></marker>
            </defs>
          </svg>
        </div>
      </section>

      {/* ControllerRouter API */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>ControllerRouter API</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The router is instantiated internally by the <code className="text-aquilia-500">ControllerEngine</code>, but you can interact with it for custom routing, testing, or debugging.
        </p>
        <CodeBlock language="python" filename="router.py">{`from aquilia.controller import ControllerRouter, ControllerCompiler

# Create compiler and router
compiler = ControllerCompiler()
router = ControllerRouter()

# Compile controllers and add to router
compiled = compiler.compile_controller(UsersController, base_prefix="/api")
router.add_controller(compiled)

# Initialize the pattern matcher (must call before matching)
router.initialize()

# Match a request
match = await router.match("/api/users/42", "GET")
if match:
    print(match.route.full_path)      # "/api/users/«id:int»"
    print(match.params)               # {"id": 42}
    print(match.route.controller_class.__name__)  # "UsersController"
    print(match.route.route_metadata.handler_name)  # "get_user"`}</CodeBlock>
      </section>

      {/* Pattern Matching */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Pattern Matching</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia uses the <code className="text-aquilia-500">«name:type»</code> syntax for typed URL parameters. The pattern compiler validates types at compile time and casts values at match time.
        </p>

        <div className={`overflow-hidden rounded-xl border mb-6 ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Pattern</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Matches</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Params</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { pattern: '/users/«id:int»', matches: '/users/42', params: '{"id": 42}' },
                { pattern: '/posts/«slug:str»', matches: '/posts/hello-world', params: '{"slug": "hello-world"}' },
                { pattern: '/items/«price:float»', matches: '/items/19.99', params: '{"price": 19.99}' },
                { pattern: '/flags/«active:bool»', matches: '/flags/true', params: '{"active": true}' },
                { pattern: '/files/«path»', matches: '/files/docs/readme', params: '{"path": "docs/readme"}' },
              ].map((r, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{r.pattern}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{r.matches}</td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{r.params}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Specificity */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Specificity-Based Resolution</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When multiple routes could match the same URL, Aquilia resolves the ambiguity using a specificity score. Higher scores are matched first.
        </p>
        <div className="space-y-3 mb-6">
          {[
            { segment: 'Static segment (e.g., /users)', score: '100 pts', color: 'text-aquilia-400' },
            { segment: 'Typed parameter (e.g., «id:int»)', score: '50 pts', color: 'text-blue-400' },
            { segment: 'Untyped parameter (e.g., «slug»)', score: '25 pts', color: 'text-yellow-400' },
            { segment: 'Wildcard / catch-all', score: '1 pt', color: 'text-gray-400' },
          ].map((item, i) => (
            <div key={i} className={boxClass + ' flex items-center justify-between'}>
              <span className={isDark ? 'text-gray-300' : 'text-gray-700'}>{item.segment}</span>
              <span className={`font-mono font-bold ${item.color}`}>{item.score}</span>
            </div>
          ))}
        </div>
        <CodeBlock language="python" filename="Specificity Example">{`# These routes are sorted by specificity automatically:
# 1. GET /users/admin    → score 200 (static + static)
# 2. GET /users/«id:int» → score 150 (static + typed)
# 3. GET /users/«slug»   → score 125 (static + untyped)

class UsersController(Controller):
    prefix = "/users"

    @GET("/admin")          # Matched FIRST for /users/admin
    async def admin(self, ctx):
        return {"page": "admin"}

    @GET("/«id:int»")      # Matched for /users/42
    async def by_id(self, ctx, id: int):
        return {"id": id}

    @GET("/«slug»")        # Matched for /users/john-doe
    async def by_slug(self, ctx, slug: str):
        return {"slug": slug}`}</CodeBlock>
      </section>

      {/* Reverse URL Generation */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Reverse URL Generation</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">url_for()</code> method generates URLs from handler names and parameters, avoiding hardcoded paths in your application.
        </p>
        <CodeBlock language="python" filename="url_for()">{`# Generate URLs by handler name
url = router.url_for("UsersController.by_id", id=42)
# → "/users/42"

url = router.url_for("UsersController.by_slug", slug="john-doe")
# → "/users/john-doe"

# With query parameters
url = router.url_for("UsersController.list", page=2, limit=20)
# → "/users/?page=2&limit=20"`}</CodeBlock>
      </section>

      {/* Conflict Detection */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Route Conflict Detection</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The compiler automatically detects ambiguous routes at compile time. Two routes conflict when they have the same HTTP method and their URL patterns could match the same request.
        </p>
        <CodeBlock language="python" filename="Conflict Detection">{`from aquilia.controller import ControllerCompiler

compiler = ControllerCompiler()

# Compile all controllers
compiled_a = compiler.compile_controller(UsersController)
compiled_b = compiler.compile_controller(ProfileController)

# Check for conflicts across the entire route tree
conflicts = compiler.validate_route_tree([compiled_a, compiled_b])

for conflict in conflicts:
    print(f"CONFLICT: {conflict['method']} {conflict['route1']['path']}")
    print(f"      vs: {conflict['route2']['path']}")
    print(f"  Reason: {conflict['reason']}")`}</CodeBlock>
      </section>

      {/* Route Inspection */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Route Inspection</h2>
        <CodeBlock language="python" filename="Inspecting Routes">{`# List all registered routes
for route_info in router.get_routes():
    print(f"{route_info['method']:6} {route_info['path']:30} → "
          f"{route_info['controller']}.{route_info['handler']} "
          f"(specificity: {route_info['specificity']})")

# Output:
# GET    /api/users/                    → UsersController.list (specificity: 100)
# GET    /api/users/«id:int»            → UsersController.get_user (specificity: 150)
# POST   /api/users/                    → UsersController.create (specificity: 100)
# PUT    /api/users/«id:int»            → UsersController.update (specificity: 150)
# DELETE /api/users/«id:int»            → UsersController.delete (specificity: 150)

# Check if a specific route exists
exists = router.has_route("GET", "/api/users/42")  # True

# Get compiled controller by name
ctrl = router.get_controller("UsersController")`}</CodeBlock>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/controllers/compiler" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Controller Compiler
        </Link>
        <Link to="/docs/controllers/openapi" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          OpenAPI Generation <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
