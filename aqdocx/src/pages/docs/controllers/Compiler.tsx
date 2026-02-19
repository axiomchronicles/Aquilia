import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Hammer, Layers, Code, Zap, AlertCircle, ArrowRight, Shield } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function ControllersCompiler() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Hammer className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                ControllerCompiler
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller.compiler — Compile controllers to executable routes</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>ControllerCompiler</code> bridges metadata extraction and route registration.
          It takes controller classes, extracts their decorator metadata, compiles URL patterns
          via <code>aquilia.patterns</code>, calculates route specificity, detects conflicts,
          and produces <code>CompiledRoute</code> / <code>CompiledController</code> objects
          ready for the router.
        </p>
      </div>

      {/* Data structures */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Data Structures
        </h2>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>CompiledRoute</h3>

        <CodeBlock
          code={`@dataclass
class CompiledRoute:
    """A compiled controller route with pattern and handler."""
    controller_class: type                # The Controller class
    controller_metadata: ControllerMetadata   # Class-level metadata
    route_metadata: RouteMetadata            # Method-level metadata
    compiled_pattern: CompiledPattern        # Compiled URL pattern (regex + castors)
    full_path: str                           # Full URL path (prefix + path_template)
    http_method: str                         # GET, POST, etc.
    specificity: int                         # Route specificity score
    app_name: Optional[str] = None           # Module/app name for fault reporting`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>CompiledController</h3>

        <CodeBlock
          code={`@dataclass
class CompiledController:
    """A fully compiled controller with all routes."""
    controller_class: type              # The Controller class
    metadata: ControllerMetadata        # Class-level metadata
    routes: List[CompiledRoute]         # All compiled routes, sorted by specificity`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Metadata Classes</h3>

        <CodeBlock
          code={`@dataclass
class ParameterMetadata:
    """Metadata for a route method parameter."""
    name: str                            # Parameter name
    type: Type                           # Type annotation
    default: Any = inspect.Parameter.empty  # Default value
    source: str = 'query'                # 'path', 'query', 'body', 'header', 'di'
    required: bool = True                # Whether required
    pattern: Optional[str] = None        # Regex pattern for validation

@dataclass
class RouteMetadata:
    """Metadata for a single route (controller method)."""
    http_method: str                     # GET, POST, etc.
    path_template: str                   # URL path with parameters
    full_path: str                       # Prefix + path_template
    handler_name: str                    # Method name
    parameters: List[ParameterMetadata]  # Method parameters
    pipeline: List[Any]                  # Method-level pipeline
    summary: str                         # OpenAPI summary
    description: str                     # OpenAPI description
    tags: List[str]                      # OpenAPI tags
    deprecated: bool                     # Deprecated flag
    response_model: Optional[Type]       # Response type
    status_code: int                     # Default status code
    specificity: int                     # Route specificity score

@dataclass
class ControllerMetadata:
    """Complete metadata for a Controller class."""
    class_name: str                      # Controller class name
    module_path: str                     # Full import path
    prefix: str                          # URL prefix
    routes: List[RouteMetadata]          # All route metadata
    pipeline: List[Any]                  # Class-level pipeline
    tags: List[str]                      # Class-level tags
    instantiation_mode: str              # "per_request" or "singleton"
    constructor_params: List[ParameterMetadata]  # Constructor DI params`}
          language="python"
        />
      </section>

      {/* Compilation flow */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Compilation Flow
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>compile_controller()</code> method performs a multi-step compilation:
        </p>

        <CodeBlock
          code={`def compile_controller(
    self,
    controller_class: type,
    base_prefix: Optional[str] = None,
) -> CompiledController:
    """
    Compile a controller class into routes.

    Steps:
    1. Extract metadata from controller class decorators
    2. For each route:
       a. Join base_prefix + controller.prefix + route.path
       b. Convert {param} syntax to «param:type» syntax
       c. Parse the pattern into a PatternAST
       d. Compile the AST into a CompiledPattern (regex + castors)
       e. Calculate route specificity
    3. Sort routes by specificity (descending)
    4. Cache the CompiledController

    Args:
        controller_class: Controller class to compile
        base_prefix: Optional base prefix from module/app

    Returns:
        CompiledController with all routes

    Raises:
        PatternSemanticError: If patterns are invalid
    """`}
          language="python"
        />
      </section>

      {/* Specificity scoring */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          Route Specificity
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Each route receives a specificity score that determines priority when multiple
          routes could match the same URL. Higher scores win:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Segment Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Score</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Example</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['Static segment', '+100', '/users/active → 200 (2 × 100)'],
                ['Typed parameter', '+50', '/users/«id:int» → 150 (100 + 50)'],
                ['Untyped parameter', '+25', '/users/«id» → 125 (100 + 25)'],
                ['Wildcard', '+1', '/users/* → 101 (100 + 1)'],
              ].map(([type_, score, example], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 text-xs font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{type_}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{score}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{example}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Routes are sorted by specificity descending, so <code>/users/active</code> (200)
          matches before <code>/users/«id:int»</code> (150).
        </p>
      </section>

      {/* Pattern syntax conversion */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Pattern Syntax Conversion
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The compiler converts between Python's curly-brace syntax and Aquilia's
          chevron syntax, using the handler's type annotations to infer parameter types:
        </p>

        <CodeBlock
          code={`# Input                            → Output
"/users/{id}"                      → "/users/«id:str»"    # default: str
"/users/{id:int}"                  → "/users/«id:int»"    # explicit type
"/users/«id:int»"                  → "/users/«id:int»"    # already chevron
"/products/{slug}"                 → "/products/«slug:str»"

# Type inference from handler signature:
@GET("/items/{id}")
async def get_item(self, ctx, id: int):  # int annotation
    ...
# Converts to: /items/«id:int» (uses param metadata type)`}
          language="python"
        />
      </section>

      {/* Conflict detection */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          Conflict Detection
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The compiler provides two conflict detection methods:
        </p>

        <h3 className={`text-lg font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          validate_route_tree() — Recommended
        </h3>

        <CodeBlock
          code={`def validate_route_tree(
    self,
    compiled_controllers: List[CompiledController],
) -> List[Dict[str, Any]]:
    """
    Validate the entire compiled route tree for conflicts.
    Accounts for applied prefixes and mounted locations.

    Returns: List of conflict descriptions, each containing:
    {
        "method": "GET",
        "route1": {"controller": "...", "path": "...", "handler": "..."},
        "route2": {"controller": "...", "path": "...", "handler": "..."},
        "reason": "Ambiguous patterns could match same request",
    }
    """`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Conflict Rules
        </h3>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Two routes conflict when they have the same HTTP method and every segment
          potentially overlaps. The compiler is smart about false positives:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Route 1</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Route 2</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Conflict?</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['/users/«id:int»', '/users/«id:int»', '✅ Yes — identical'],
                ['/users/«id:int»', '/users/«uid:int»', '✅ Yes — both dynamic int'],
                ['/users/active', '/users/«id:int»', '❌ No — static vs int, "active" is not int'],
                ['/users/active', '/users/«slug:str»', '❌ No — static-first priority resolves it'],
                ['/users/«id:int»', '/posts/«id:int»', '❌ No — different static segment'],
                ['/users', '/users/«id:int»', '❌ No — different segment count'],
              ].map(([r1, r2, conflict], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{r1}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{r2}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{conflict}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Export / inspection */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          Exporting Routes
        </h2>

        <CodeBlock
          code={`def export_routes(self, controllers: List[CompiledController]) -> Dict[str, Any]:
    """Export all compiled routes for inspection/debugging."""
    return {
        "controllers": [c.to_dict() for c in controllers],
        "total_routes": sum(len(c.routes) for c in controllers),
        "conflicts": self.validate_route_tree(controllers),
    }

# Usage:
compiler = ControllerCompiler()
compiled = [compiler.compile_controller(ctrl) for ctrl in controllers]
report = compiler.export_routes(compiled)
print(f"Total routes: {report['total_routes']}")
print(f"Conflicts: {len(report['conflicts'])}")`}
          language="python"
        />
      </section>

      {/* Navigation */}
      <section className="mb-10">
        <div className="flex justify-between">
          <Link to="/docs/controllers/engine" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ← ControllerEngine
          </Link>
          <Link to="/docs/controllers/router" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ControllerRouter →
          </Link>
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}