import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { Cpu, Layers, Zap, Shield, ArrowRight, AlertCircle, Filter, Code } from 'lucide-react'

export function ControllersEngine() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                ControllerEngine
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller.engine — Route dispatch and execution</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>ControllerEngine</code> is the central execution component that ties together
          controller instantiation (via <code>ControllerFactory</code>), pipeline execution,
          parameter binding, serialization, filtering/pagination, content negotiation,
          lifecycle hooks, and fault handling.
        </p>
      </div>

      {/* Class definition */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          Class Definition
        </h2>

        <CodeBlock
          code={`class ControllerEngine:
    # Class-level caches shared across instances
    _signature_cache: Dict[Any, inspect.Signature] = {}
    _pipeline_param_cache: Dict[int, set] = {}  # id(callable) -> param names
    _has_lifecycle_hooks: Dict[type, tuple] = {} # class -> (has_on_request, has_on_response)
    _simple_route_cache: Dict[int, bool] = {}    # id(route) -> is_simple
    _is_coro_cache: Dict[int, bool] = {}         # id(func) -> is_coroutine

    def __init__(
        self,
        factory: ControllerFactory,
        enable_lifecycle: bool = True,
        fault_engine: Optional[Any] = None,
    ):
        self.factory = factory
        self.enable_lifecycle = enable_lifecycle
        self.fault_engine = fault_engine`}
          language="python"
        />
      </section>

      {/* execute() method */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          execute() — The Main Entry Point
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>execute()</code> method is called by the <code>ASGIAdapter</code> after the
          router matches a request to a <code>CompiledRoute</code>. It orchestrates the full
          request execution pipeline:
        </p>

        <CodeBlock
          code={`async def execute(
    self,
    route: CompiledRoute,
    request: Request,
    path_params: Dict[str, Any],
    container: Container,
) -> Response:`}
          language="python"
        />

        <div className={`space-y-3 mt-4`}>
          {[
            { step: '1', title: 'Fast Path Check', desc: 'If the route has a monkeypatched handler (e.g., OpenAPI doc routes), it\'s called directly without any DI or lifecycle.' },
            { step: '2', title: 'Build RequestCtx', desc: 'Constructs a RequestCtx inline from request.state (identity, session) and the DI container.' },
            { step: '3', title: 'Singleton Lifecycle Init', desc: 'For singleton controllers, calls on_startup exactly once (tracked via _lifecycle_initialized set).' },
            { step: '4', title: 'Instantiate Controller', desc: 'Uses ControllerFactory.create() with DI resolution.' },
            { step: '5', title: 'Execute Class Pipeline', desc: 'Runs class-level pipeline nodes (guards, transforms). If a guard returns a Response, execution stops.' },
            { step: '6', title: 'Execute Method Pipeline', desc: 'Runs method-level pipeline nodes (from decorator\'s pipeline parameter).' },
            { step: '7', title: 'Simple Route Fast Path', desc: 'If the route has no serializers, blueprints, filters, or complex params, the handler is called directly (skipping _bind_parameters).' },
            { step: '8', title: 'Bind Parameters', desc: 'For complex routes: resolves path params, query params, body (JSON/form), serializer injection, blueprint injection, and DI params.' },
            { step: '9', title: 'Execute Handler', desc: 'Calls the controller method with ctx + bound parameters.' },
            { step: '10', title: 'Post-processing', desc: 'Applies filters/pagination, response serializer, response blueprint, and content negotiation.' },
            { step: '11', title: 'Lifecycle Hooks', desc: 'Calls on_request before and on_response after (only if overridden — checked via MRO cache).' },
            { step: '12', title: 'Fault Handling', desc: 'On exception, reports to FaultEngine (if configured) then re-raises for middleware to handle.' },
          ].map(({ step, title, desc }) => (
            <div key={step} className={`rounded-xl border p-4 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-aquilia-500/20 text-aquilia-400 flex items-center justify-center text-xs font-bold">{step}</span>
                <div>
                  <h4 className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</h4>
                  <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Simple route detection */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Simple Route Fast Path
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The engine classifies routes as "simple" when they have no serializers, blueprints,
          filters, pagination, renderers, or complex parameters. Simple routes skip the full
          <code>_bind_parameters</code> machinery for faster execution:
        </p>

        <CodeBlock
          code={`# Route is classified as "simple" when:
is_simple = (
    not route.controller_metadata.pipeline    # No class pipeline
    and not route_metadata.pipeline           # No method pipeline
    and not has_serializer                    # No request/response serializer
    and not has_blueprint                     # No request/response blueprint
    and not has_filters_or_pagination         # No filterset/search/ordering/pagination
    and (not params or all(                   # Only ctx and path params
        p.name == 'ctx' or p.source == 'path'
        for p in params
    ))
)

# Simple routes get a direct call:
if is_simple:
    if path_params:
        result = await handler_method(ctx, **path_params)
    else:
        result = await handler_method(ctx)
    return self._to_response(result)`}
          language="python"
        />
      </section>

      {/* Parameter binding */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          Parameter Binding
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>_bind_parameters()</code> method resolves handler arguments from multiple
          sources based on their <code>ParameterMetadata.source</code>:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Source</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Resolution</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['path', 'From URL path parameters (e.g., id from /users/«id:int»)'],
                ['query', 'From URL query string (?key=value), auto-cast to annotation type'],
                ['body', 'From JSON/form request body, extracted by field name'],
                ['di', 'From DI container — special handling for Session and Identity types'],
                ['(Serializer type)', 'Auto-parsed: creates serializer with data=body, calls is_valid(raise_fault=True)'],
                ['(Blueprint type)', 'Auto-parsed: creates blueprint with data=body, calls is_sealed(raise_fault=True)'],
              ].map(([source, resolution], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{source}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{resolution}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Serializer Injection</h3>

        <CodeBlock
          code={`# When a parameter is typed as a Serializer subclass:
@POST("/")
async def create(self, ctx: RequestCtx, data: CreateUserSerializer):
    # 'data' receives serializer.validated_data (dict)
    ...

# To get the full serializer instance, name it with _serializer suffix:
@POST("/")
async def create(self, ctx: RequestCtx, user_serializer: CreateUserSerializer):
    # user_serializer is the full Serializer instance
    user_serializer.save()
    ...`}
          language="python"
        />

        <h3 className={`text-lg font-semibold mt-6 mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Blueprint Injection</h3>

        <CodeBlock
          code={`# When a parameter is typed as a Blueprint subclass:
@POST("/")
async def create(self, ctx: RequestCtx, data: UserBlueprint):
    # 'data' receives blueprint.validated_data

# For ProjectedRef (Blueprint["projection"]):
@PATCH("/«id:int»", request_blueprint=UserBlueprint["partial"])
async def update(self, ctx: RequestCtx, id: int) -> Response:
    body = await ctx.json()
    # Body is auto-validated through UserBlueprint with "partial" projection
    ...

# Name with _blueprint or _bp suffix to get the full instance:
@POST("/")
async def create(self, ctx: RequestCtx, user_blueprint: UserBlueprint):
    # user_blueprint is the full Blueprint instance
    ...`}
          language="python"
        />
      </section>

      {/* Post-processing pipeline */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Filter className="w-5 h-5 text-aquilia-400" />
          Post-Processing Pipeline
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          After the handler returns, the engine applies a post-processing pipeline
          (only for non-simple routes):
        </p>

        <CodeBlock
          code={`# After handler execution:
result = await handler_method(ctx, **kwargs)

# 1. Filters & Pagination (if configured on the decorator)
result = await self._apply_filters_and_pagination(result, route_metadata, request)

# 2. Response Serializer (auto-serializes if response_serializer is set)
result = self._apply_response_serializer(result, route_metadata, ctx)

# 3. Response Blueprint (auto-molds if response_blueprint is set)
result = self._apply_response_blueprint(result, route_metadata, ctx)

# 4. Content Negotiation (if renderer_classes is set)
response = self._apply_content_negotiation(result, route_metadata, request)
if response is None:
    response = self._to_response(result)

# 5. Lifecycle hook
if has_on_response:
    await controller.on_response(ctx, response)`}
          language="python"
        />
      </section>

      {/* Pipeline execution */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          Pipeline Node Execution
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Pipeline nodes are called with intelligent parameter injection — the engine inspects
          each node's signature (cached by <code>id(callable)</code>) and passes only the
          parameters it declares:
        </p>

        <CodeBlock
          code={`async def _execute_pipeline_node(self, pipeline_node, request, ctx, controller):
    # Cached signature inspection (by id of callable)
    param_names = self._pipeline_param_cache.get(id(pipeline_node))
    if param_names is None:
        sig = inspect.signature(pipeline_node)
        param_names = set(sig.parameters.keys())
        self._pipeline_param_cache[id(pipeline_node)] = param_names

    kwargs = {}
    if "request" in param_names or "req" in param_names:
        kwargs["request" if "request" in param_names else "req"] = request
    if "ctx" in param_names or "context" in param_names:
        kwargs["ctx" if "ctx" in param_names else "context"] = ctx
    if "controller" in param_names:
        kwargs["controller"] = controller

    result = await self._safe_call(pipeline_node, **kwargs)

    # False → 403, Response → return it, anything else → continue
    if result is False:
        return Response.json({"error": "Pipeline guard failed"}, status=403)
    elif isinstance(result, Response):
        return result
    return None`}
          language="python"
        />
      </section>

      {/* _to_response conversion */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Return Value Conversion
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The <code>_to_response()</code> method converts handler return values to
          <code>Response</code> objects:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Return Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Conversion</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['Response', 'Returned as-is'],
                ['dict', 'Response.json(result) — application/json'],
                ['list / tuple', 'Response.json(result) — application/json'],
                ['str', 'Response(result, content_type="text/plain")'],
                ['None', 'Response("", status=204) — No Content'],
                ['Other', 'Response.json({"result": str(result)})'],
              ].map(([type_, conversion], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{type_}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{conversion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Fault integration */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <AlertCircle className="w-5 h-5 text-aquilia-400" />
          Fault Engine Integration
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          When an exception occurs during handler execution, the engine reports it to
          the <code>FaultEngine</code> (if configured) before re-raising:
        </p>

        <CodeBlock
          code={`except Exception as e:
    self.logger.error(
        f"Error executing {controller_class.__name__}.{handler_name}: {e}",
        exc_info=True,
    )
    if self.fault_engine:
        try:
            await self.fault_engine.process(
                e,
                app=route.app_name,
                route=route.full_path,
                request_id=request.state.get('request_id'),
            )
        except Exception:
            pass  # Don't fail on fault processing failure
    raise  # Re-raise for ExceptionMiddleware to convert to HTTP response`}
          language="python"
        />
      </section>

      {/* Navigation */}
      <section className="mb-10">
        <div className="flex justify-between">
          <Link to="/docs/controllers/factory" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ← ControllerFactory
          </Link>
          <Link to="/docs/controllers/compiler" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ControllerCompiler →
          </Link>
        </div>
      </section>
    </div>
  )
}
