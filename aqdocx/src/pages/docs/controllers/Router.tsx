import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Navigation, Layers, Zap, Code, ArrowRight, Search, Link2 } from 'lucide-react'

export function ControllersRouter() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Navigation className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>ControllerRouter</h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller.router — Two-tier URL matching engine</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>ControllerRouter</code> is a high-performance pattern-matching router
          with a two-tier architecture: <strong>O(1) dict lookup</strong> for static routes
          and <strong>O(k) regex matching</strong> for parameterized routes (where k = number
          of segments).
        </p>
      </div>

      {/* Architecture */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Two-Tier Architecture
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Tier 1: Static Routes</h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              <li>• <strong>O(1)</strong> hash map lookup</li>
              <li>• For routes with no path or query params</li>
              <li>• Paths normalized (trailing slash stripped)</li>
              <li>• Example: <code>GET /api/health</code></li>
              <li>• Indexed as: <code>{`{method: {path: (route, {}, {})}}`}</code></li>
            </ul>
          </div>

          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Tier 2: Dynamic Routes</h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              <li>• <strong>O(k)</strong> compiled regex matching</li>
              <li>• For routes with <code>«name:type»</code> params</li>
              <li>• Params extracted and type-cast in one pass</li>
              <li>• Validators run on extracted values</li>
              <li>• Sorted by specificity (most specific first)</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Class definition */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          Class Definition
        </h2>

        <CodeBlock
          code={`class ControllerRouter:
    def __init__(self):
        self.compiled_controllers: List[CompiledController] = []
        self.routes_by_method: Dict[str, List[CompiledRoute]] = {}
        self.matcher = PatternMatcher()
        self._initialized = False

        # ── Fast-path indexes (built during initialize) ──
        # {method: {path: (route, empty_params, empty_query)}}
        self._static_routes: Dict[str, Dict[str, Tuple]] = {}
        # {method: list[(compiled_pattern, route, param_names)]}
        self._dynamic_routes: Dict[str, List[Tuple]] = {}

# Reused empty dicts to avoid per-request allocations
_EMPTY_DICT: Dict[str, Any] = {}
_EMPTY_QUERY: Dict[str, str] = {}`}
          language="python"
        />
      </section>

      {/* ControllerRouteMatch */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Search className="w-5 h-5 text-aquilia-400" />
          ControllerRouteMatch
        </h2>

        <CodeBlock
          code={`@dataclass
class ControllerRouteMatch:
    """Result of a successful controller route match."""
    route: CompiledRoute       # The matched CompiledRoute
    params: Dict[str, Any]     # Extracted and type-cast path parameters
    query: Dict[str, Any]      # Extracted and validated query parameters`}
          language="python"
        />
      </section>

      {/* match_sync */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          match_sync() — The Hot Path
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The core matching method is synchronous for maximum performance. An
          <code>async match()</code> wrapper exists for compatibility:
        </p>

        <CodeBlock
          code={`def match_sync(
    self,
    path: str,
    method: str,
    query_params: Optional[Dict[str, str]] = None,
) -> Optional[ControllerRouteMatch]:
    """Synchronous O(1)/O(k) route matching."""
    if not self._initialized:
        self.initialize()

    # ── Tier 1: Static O(1) lookup ──
    static_map = self._static_routes.get(method)
    if static_map:
        norm_path = path.rstrip('/') or '/'
        hit = static_map.get(norm_path)
        if hit is not None:
            return ControllerRouteMatch(
                route=hit[0], params=hit[1], query=hit[2]
            )

    # ── Tier 2: Dynamic regex matching ──
    dynamic_list = self._dynamic_routes.get(method)
    if dynamic_list:
        for cp, route, param_names in dynamic_list:
            m = cp.compiled_re.match(path)
            if m is None:
                continue

            # Extract, cast, and validate params
            params = {}
            valid = True
            for name in param_names:
                value_str = m.group(name)
                param_meta = cp.params[name]
                try:
                    value = param_meta.castor(value_str)
                    for v in param_meta.validators:
                        if not v(value):
                            valid = False
                            break
                    if not valid:
                        break
                    params[name] = value
                except (ValueError, TypeError):
                    valid = False
                    break

            if not valid:
                continue

            # Process query params similarly...
            return ControllerRouteMatch(
                route=route, params=params, query=query
            )

    return None`}
          language="python"
        />
      </section>

      {/* Initialize */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          initialize()
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>initialize()</code> method builds the fast-path indexes from compiled
          controllers. It's called lazily on first <code>match()</code> or explicitly:
        </p>

        <CodeBlock
          code={`def initialize(self):
    """Build fast-path lookup structures."""
    for method, routes in self.routes_by_method.items():
        # Sort by specificity (descending)
        routes.sort(key=lambda r: r.specificity, reverse=True)

        for route in routes:
            cp = route.compiled_pattern
            has_params = bool(cp.params)
            has_query = bool(cp.query)

            if not has_params and not has_query:
                # Pure static route → O(1) lookup
                path = route.full_path.rstrip('/') or '/'
                static_map[path] = (route, _EMPTY_DICT, _EMPTY_DICT)
            else:
                # Dynamic route → regex matching
                param_names = list(cp.params.keys())
                dynamic_list.append((cp, route, param_names))

    self._initialized = True`}
          language="python"
        />
      </section>

      {/* url_for */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Link2 className="w-5 h-5 text-aquilia-400" />
          Reverse URL Generation
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>url_for()</code> method generates URLs from route names and parameters:
        </p>

        <CodeBlock
          code={`def url_for(self, name: str, **params) -> str:
    """
    Reverse URL generation.

    Args:
        name: "ControllerName.method_name" or just "method_name"
        **params: Path and query parameters

    Returns:
        Generated URL string

    Raises:
        ValueError: If no route found with the given name

    Examples:
        router.url_for("UsersController.get_user", id=42)
        # → "/api/users/42"

        router.url_for("get_user", id=42, include_posts=True)
        # → "/api/users/42?include_posts=True"
    """`}
          language="python"
        />

        <CodeBlock
          code={`# In a controller:
@GET("/«id:int»")
async def get_user(self, ctx: RequestCtx, id: int) -> Response:
    # Generate URL for another route
    detail_url = ctx.container.resolve(ControllerRouter).url_for(
        "UsersController.get_user", id=id
    )
    return Response.json({"url": detail_url})`}
          language="python"
        />
      </section>

      {/* Utility methods */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Utility Methods
        </h2>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Method</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Returns</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['add_controller(compiled)', 'None', 'Add a CompiledController and its routes. Marks router as uninitialized.'],
                ['initialize()', 'None', 'Build fast-path static/dynamic indexes. Called lazily on first match.'],
                ['match_sync(path, method, query)', 'Optional[Match]', 'Synchronous route matching — the hot path.'],
                ['match(path, method, query)', 'Optional[Match]', 'Async wrapper around match_sync().'],
                ['get_routes()', 'List[Dict]', 'Get all routes as dicts (method, path, controller, handler, specificity).'],
                ['get_routes_full()', 'List[CompiledRoute]', 'Get all CompiledRoute objects.'],
                ['get_controller(name)', 'Optional[CompiledController]', 'Get compiled controller by class name.'],
                ['has_route(method, path)', 'bool', 'Check if a route exists for the given method and path.'],
                ['url_for(name, **params)', 'str', 'Reverse URL generation with path and query params.'],
              ].map(([method, ret, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{method}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{ret}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Performance notes */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Performance Notes
        </h2>

        <div className={`space-y-3`}>
          {[
            { title: 'Static routes: O(1)', desc: 'Pure dict lookup per method. Normalized paths (trailing slash stripped). Pre-allocated empty dicts shared across all static matches to avoid per-request allocation.' },
            { title: 'Dynamic routes: O(k)', desc: 'k = number of route patterns for the HTTP method. Routes sorted by specificity so the most specific pattern is tried first. Compiled regex is used for matching and param extraction in a single pass.' },
            { title: 'Lazy initialization', desc: 'The fast-path indexes (_static_routes, _dynamic_routes) are built on first match() call. Adding a controller marks the router as uninitialized, triggering a rebuild on the next match.' },
            { title: 'Shared empty dicts', desc: '_EMPTY_DICT and _EMPTY_QUERY are module-level singletons reused for static route matches to avoid garbage collection pressure.' },
          ].map(({ title, desc }, i) => (
            <div key={i} className={`rounded-xl border p-4 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
              <h4 className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</h4>
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Navigation */}
      <section className="mb-10">
        <div className="flex justify-between">
          <Link to="/docs/controllers/compiler" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ← ControllerCompiler
          </Link>
          <Link to="/docs/controllers/openapi" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            OpenAPI Generation →
          </Link>
        </div>
      </section>
    </div>
  )
}
