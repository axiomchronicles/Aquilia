import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Factory, Layers, Zap, Shield, Code, ArrowRight, AlertCircle } from 'lucide-react'

export function ControllersFactory() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Factory className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                ControllerFactory
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller.factory — DI-powered controller instantiation</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>ControllerFactory</code> is responsible for creating controller instances
          with full dependency injection support. It handles both <code>per_request</code> and
          <code>singleton</code> instantiation modes, lifecycle hooks, and scope validation.
        </p>
      </div>

      {/* InstantiationMode */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          InstantiationMode Enum
        </h2>

        <CodeBlock
          code={`class InstantiationMode(str, Enum):
    """Controller instantiation modes."""
    PER_REQUEST = "per_request"  # New instance per HTTP request
    SINGLETON = "singleton"     # Single shared instance`}
          language="python"
        />
      </section>

      {/* Class definition */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          ControllerFactory Class
        </h2>

        <CodeBlock
          code={`class ControllerFactory:
    # Class-level caches for constructor analysis
    _ctor_info_cache: Dict[Type, Any] = {}  # class -> param specs

    def __init__(self, app_container: Optional[Any] = None):
        self.app_container = app_container
        self._singletons: Dict[Type, Any] = {}
        self._startup_called: set = set()`}
          language="python"
        />

        <div className={`rounded-xl border overflow-hidden mt-4 ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Attribute</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['app_container', 'Optional[Container]', 'The application-scope DI container (singleton scope resolution)'],
                ['_singletons', 'Dict[Type, Any]', 'Cache of singleton controller instances'],
                ['_startup_called', 'set', 'Track which singleton controllers have had on_startup called'],
                ['_ctor_info_cache', 'Dict[Type, Any]', 'Class-level cache of analyzed constructor signatures (shared across instances)'],
                ['_no_on_request', 'set', 'Class-level set of controllers known to NOT override on_request'],
              ].map(([attr, type_, desc], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{attr}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{type_}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* create() method */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          create() Method
        </h2>

        <CodeBlock
          code={`async def create(
    self,
    controller_class: Type,
    mode: InstantiationMode = InstantiationMode.PER_REQUEST,
    request_container: Optional[Any] = None,
    ctx: Optional[Any] = None,
) -> Any:
    """
    Create controller instance.

    Args:
        controller_class: Controller class to instantiate
        mode: PER_REQUEST or SINGLETON
        request_container: Request-scoped DI container
        ctx: Request context for lifecycle hooks

    Returns:
        Controller instance with all dependencies injected

    Raises:
        ScopeViolationError: If injecting request-scoped into singleton
    """`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>create()</code> method delegates to either <code>_create_singleton()</code> or
          <code>_create_per_request()</code> based on the mode.
        </p>
      </section>

      {/* DI resolution pipeline */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          DI Resolution Pipeline
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When the factory creates a controller, it follows this resolution pipeline:
        </p>

        <div className={`space-y-3 mb-4`}>
          {[
            { step: '1', title: 'Analyze Constructor', desc: '_analyze_constructor() inspects the __init__ signature and type hints. Results are cached in _ctor_info_cache (class-level, shared across instances) so inspect.signature() is called only once per controller class.' },
            { step: '2', title: 'Check for No-DI Fast Path', desc: 'If the constructor has no injectable parameters (no type annotations), the controller is instantiated directly without DI resolution.' },
            { step: '3', title: 'Resolve Each Parameter', desc: '_resolve_parameter() resolves each constructor parameter from the DI container. Supports Annotated[T, Inject(tag=...)] syntax for tagged injection.' },
            { step: '4', title: 'Handle Defaults', desc: 'If resolution fails but the parameter has a default value, the default is used. If the default itself is a type (isinstance(default, type)), it\'s treated as a type hint for DI.' },
            { step: '5', title: 'Instantiate', desc: 'controller_class(**params) is called with all resolved dependencies.' },
            { step: '6', title: 'Lifecycle Hooks', desc: 'For singletons: on_startup is called once. For per_request: on_request is called if overridden (fast-path skip via _no_on_request cache).' },
          ].map(({ step, title, desc }) => (
            <div key={step} className={`rounded-xl border p-4 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-sm font-bold">{step}</span>
                <div>
                  <h4 className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</h4>
                  <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Constructor analysis */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          Constructor Analysis
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>_analyze_constructor()</code> static method inspects a controller's
          <code>__init__</code> and returns a list of tuples describing each parameter:
        </p>

        <CodeBlock
          code={`@staticmethod
def _analyze_constructor(controller_class: Type):
    """Returns: [(name, type, has_default, default), ...]"""
    sig = inspect.signature(controller_class.__init__)
    type_hints = get_type_hints(controller_class.__init__, include_extras=True)

    result = []
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue

        param_type = type_hints.get(param_name, param.annotation)

        # Intelligent inference: if default is a class, treat it as type hint
        if param_type is _EMPTY and param.default is not _EMPTY:
            if isinstance(param.default, type):
                param_type = param.default

        has_default = param.default is not _EMPTY
        default_val = param.default if has_default else None
        result.append((param_name, param_type, has_default, default_val))

    return result`}
          language="python"
        />

        <div className={`mt-4 p-4 rounded-xl border ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-blue-50 border-blue-200'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            <strong>Intelligent inference:</strong> If a constructor parameter has no type annotation
            but its default value is a class, the factory treats that class as the type hint.
            This allows <code>def __init__(self, cache=CacheService)</code> to work as
            <code>def __init__(self, cache: CacheService)</code>.
          </p>
        </div>
      </section>

      {/* Annotated injection */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          Annotated[T, Inject(...)] Support
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The factory supports <code>typing.Annotated</code> with <code>Inject</code> metadata
          for advanced injection (tags, tokens):
        </p>

        <CodeBlock
          code={`from typing import Annotated
from aquilia.di import Inject

class AnalyticsController(Controller):
    prefix = "/analytics"

    def __init__(
        self,
        # Standard injection (by type)
        repo: UserRepository,
        # Tagged injection (resolves by type + tag)
        cache: Annotated[CacheService, Inject(tag="analytics")],
        # Token injection (resolves by string token)
        config: Annotated[dict, Inject(token="analytics_config")],
    ):
        self.repo = repo
        self.cache = cache
        self.config = config`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The factory's <code>_resolve_parameter()</code> method detects <code>Annotated</code>
          and extracts <code>Inject</code> metadata using duck typing (checking for
          <code>_inject_tag</code> or <code>_inject_token</code> attributes).
        </p>
      </section>

      {/* Singleton lifecycle */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          Singleton Lifecycle
        </h2>

        <CodeBlock
          code={`# Singleton creation flow:
async def _create_singleton(self, controller_class, ctx):
    # 1. Return cached instance if it exists
    if controller_class in self._singletons:
        return self._singletons[controller_class]

    # 2. Validate scope safety (no request-scoped deps in singleton)
    self.validate_scope(controller_class, InstantiationMode.SINGLETON)

    # 3. Resolve from app_container (not request container)
    instance = await self._resolve_and_instantiate(
        controller_class, self.app_container
    )

    # 4. Call on_startup hook (exactly once)
    if controller_class not in self._startup_called:
        await instance.on_startup(ctx)
        self._startup_called.add(controller_class)

    # 5. Cache the instance
    self._singletons[controller_class] = instance
    return instance`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Shutdown</h3>

        <CodeBlock
          code={`async def shutdown(self):
    """Shutdown all singleton controllers. Called by AquiliaServer."""
    for controller_class, instance in self._singletons.items():
        if hasattr(instance, 'on_shutdown'):
            try:
                await instance.on_shutdown(None)
            except Exception as e:
                print(f"Error in {controller_class.__name__}.on_shutdown: {e}")`}
          language="python"
        />
      </section>

      {/* Per-request fast path */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Per-Request Fast Path
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The factory optimizes per-request instantiation by caching whether a controller
          overrides <code>on_request</code>. Controllers that don't override it skip the
          lifecycle hook check entirely:
        </p>

        <CodeBlock
          code={`# Fast path: skip on_request for controllers that don't override it
_no_on_request: set = set()  # Class-level cache

async def _create_per_request(self, controller_class, request_container, ctx):
    instance = await self._resolve_and_instantiate(
        controller_class, request_container or self.app_container,
    )

    if controller_class not in ControllerFactory._no_on_request:
        # Check MRO: is on_request actually overridden?
        has_custom_on_request = (
            'on_request' in controller_class.__dict__
            or any('on_request' in B.__dict__
                   for B in controller_class.__mro__[1:]
                   if B.__name__ != 'Controller' and B is not object)
        )
        if has_custom_on_request:
            await instance.on_request(ctx)
        else:
            ControllerFactory._no_on_request.add(controller_class)

    return instance`}
          language="python"
        />
      </section>

      {/* Navigation */}
      <section className="mb-10">
        <div className="flex justify-between">
          <Link to="/docs/controllers/request-ctx" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ← RequestCtx
          </Link>
          <Link to="/docs/controllers/engine" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ControllerEngine →
          </Link>
        </div>
      </section>
    </div>
  )
}
