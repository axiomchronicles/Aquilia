import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowRight, GitBranch } from 'lucide-react'

export function RoutingOverview() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <GitBranch className="w-4 h-4" />
          Core / Routing
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Routing
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia uses a compile-time pattern matching router. Routes are declared via controller decorators, compiled at startup by the <code className="text-aquilia-500">ControllerCompiler</code>, and matched at runtime by the <code className="text-aquilia-500">ControllerRouter</code> with specificity-based resolution and typed parameters.
        </p>
      </div>

      {/* How Routing Works */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Route Declaration</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Routes are declared using HTTP method decorators on controller methods. The controller's <code className="text-aquilia-500">prefix</code> is prepended to each route path.
        </p>
        <CodeBlock language="python" filename="controller.py">{`from aquilia import Controller, Get, Post, Put, Delete


class ArticleController(Controller):
    prefix = "/api/articles"

    @Get("/")
    async def list_articles(self, ctx):
        """GET /api/articles/ — list all articles"""
        ...

    @Get("/{id:int}")
    async def get_article(self, ctx, id: int):
        """GET /api/articles/42 — get single article"""
        ...

    @Get("/{slug:str}")
    async def get_by_slug(self, ctx, slug: str):
        """GET /api/articles/hello-world — get by slug"""
        ...

    @Post("/")
    async def create_article(self, ctx):
        """POST /api/articles/ — create article"""
        ...

    @Put("/{id:int}")
    async def update_article(self, ctx, id: int):
        """PUT /api/articles/42 — update article"""
        ...

    @Delete("/{id:int}")
    async def delete_article(self, ctx, id: int):
        """DELETE /api/articles/42 — delete article"""
        ...`}</CodeBlock>
      </section>

      {/* Pattern Types */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>URL Pattern Types</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Pattern</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Example Match</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Specificity</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { p: '/users/admin', t: 'Static', e: '/users/admin', s: '100/segment' },
                { p: '/{id:int}', t: 'Integer', e: '/42 → id=42', s: '50/segment' },
                { p: '/{name:str}', t: 'String', e: '/john → name="john"', s: '25/segment' },
                { p: '/{price:float}', t: 'Float', e: '/19.99 → price=19.99', s: '50/segment' },
                { p: '/{active:bool}', t: 'Boolean', e: '/true → active=True', s: '50/segment' },
                { p: '/{path:path}', t: 'Path', e: '/a/b/c → path="a/b/c"', s: '1/segment' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.p}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.e}</td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.s}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Specificity */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Specificity Resolution</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When multiple routes could match the same URL, the router picks the most specific one. Static segments score highest, typed parameters score medium, and catch-alls score lowest.
        </p>
        <CodeBlock language="python" filename="specificity.py">{`# Given these routes:
@Get("/users/admin")        # Specificity: 200 (static + static)
@Get("/users/{id:int}")     # Specificity: 150 (static + typed)
@Get("/users/{slug:str}")   # Specificity: 125 (static + untyped)

# Request: GET /users/admin → matches "/users/admin" (score 200)
# Request: GET /users/42    → matches "/users/{id:int}" (score 150)
# Request: GET /users/john  → matches "/users/{slug:str}" (score 125)`}</CodeBlock>
      </section>

      {/* Reverse URLs */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Reverse URL Generation</h2>
        <CodeBlock language="python" filename="url_for.py">{`# In controllers
url = router.url_for("ArticleController.get_article", id=42)
# → "/api/articles/42"

# In templates (auto-injected)
# {{ url_for("ArticleController.get_article", id=article.id) }}`}</CodeBlock>
      </section>

      {/* Deep Dives */}
      <section>
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Deep Dives</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { title: 'Controller Router', desc: 'Pattern matching, URL params, conflict detection', to: '/docs/controllers/router' },
            { title: 'Controller Compiler', desc: 'How routes are compiled at startup', to: '/docs/controllers/compiler' },
            { title: 'Route Decorators', desc: '@Get, @Post, @Put, @Delete, @WS', to: '/docs/controllers/decorators' },
            { title: 'OpenAPI Generation', desc: 'Auto-generated API documentation', to: '/docs/controllers/openapi' },
          ].map((item, i) => (
            <Link key={i} to={item.to} className={`group p-5 rounded-xl border transition-all hover:-translate-y-0.5 ${isDark ? 'bg-[#0A0A0A] border-white/10 hover:border-aquilia-500/30' : 'bg-white border-gray-200 hover:border-aquilia-500/30'}`}>
              <h3 className={`font-bold text-sm mb-1 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {item.title}
                <ArrowRight className="w-3 h-3 text-aquilia-500 opacity-0 group-hover:opacity-100 transition" />
              </h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
