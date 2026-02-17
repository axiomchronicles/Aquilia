import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { FileJson, ArrowLeft, ArrowRight, Info } from 'lucide-react'

export function ControllersOpenAPI() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const boxClass = `p-6 rounded-2xl border ${isDark ? 'bg-[#0A0A0A] border-white/10' : 'bg-white border-gray-200'}`

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <FileJson className="w-4 h-4" />
          Core / Controllers / OpenAPI
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          OpenAPI Generation
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia automatically generates a complete OpenAPI 3.1.0 specification from your controllers. The generator introspects route metadata, type hints, docstrings, serializers, and pipeline guards to produce a fully documented API spec — with Swagger UI and ReDoc built in.
        </p>
      </div>

      {/* Features */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Auto-Introspection Features</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { title: 'Route Paths & Methods', desc: 'Compiled patterns auto-converted to OpenAPI path templates with typed parameters' },
            { title: 'Request Body Inference', desc: 'Inferred from type hints, Annotated[..., Body()], docstrings, and source analysis' },
            { title: 'Response Schemas', desc: 'Generated from response_model, source pattern matching, and status codes' },
            { title: 'Security Schemes', desc: 'Auto-detected from pipeline guards (Bearer, API Key, OAuth2)' },
            { title: 'Tag Grouping', desc: 'Tags from controller.tags, module tags, or fallback to controller name' },
            { title: '$ref Deduplication', desc: 'Shared schemas placed in components/schemas with $ref references' },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <h3 className={`font-bold text-sm mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.title}</h3>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Configuration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>OpenAPIConfig</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Configure OpenAPI generation via <code className="text-aquilia-500">Integration.openapi()</code> in your workspace or pass an <code className="text-aquilia-500">OpenAPIConfig</code> directly.
        </p>
        <CodeBlock language="python" filename="workspace.py">{`from aquilia import Workspace, Module, Integration

workspace = Workspace(
    modules=[
        Module("api", controllers=[UsersController, ProductController]),
    ],
    integrations=[
        Integration.openapi(
            title="My API",
            version="2.0.0",
            description="Production API for my application",
            terms_of_service="https://example.com/tos",
            contact_name="API Team",
            contact_email="api@example.com",
            license_name="MIT",
            license_url="https://opensource.org/licenses/MIT",
            servers=[
                {"url": "https://api.example.com", "description": "Production"},
                {"url": "https://staging.example.com", "description": "Staging"},
            ],
            docs_path="/docs",             # Swagger UI
            openapi_json_path="/openapi.json",
            redoc_path="/redoc",
            include_internal=False,
            group_by_module=True,
            infer_request_body=True,
            infer_responses=True,
            detect_security=True,
            swagger_ui_theme="dark",
        ),
    ],
)`}</CodeBlock>
      </section>

      {/* Config Reference Table */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Configuration Reference</h2>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Option</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Type</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Default</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Description</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { o: 'title', t: 'str', d: '"Aquilia API"', desc: 'API title in the info block' },
                { o: 'version', t: 'str', d: '"1.0.0"', desc: 'API version string' },
                { o: 'description', t: 'str', d: '""', desc: 'Markdown description for the API' },
                { o: 'docs_path', t: 'str', d: '"/docs"', desc: 'Swagger UI endpoint' },
                { o: 'openapi_json_path', t: 'str', d: '"/openapi.json"', desc: 'Raw JSON spec endpoint' },
                { o: 'redoc_path', t: 'str', d: '"/redoc"', desc: 'ReDoc endpoint' },
                { o: 'include_internal', t: 'bool', d: 'False', desc: 'Include routes starting with /_' },
                { o: 'group_by_module', t: 'bool', d: 'True', desc: 'Group tags by module name' },
                { o: 'infer_request_body', t: 'bool', d: 'True', desc: 'Infer request body from source/hints' },
                { o: 'detect_security', t: 'bool', d: 'True', desc: 'Detect auth guards as security schemes' },
                { o: 'swagger_ui_theme', t: 'str', d: '""', desc: 'Swagger UI theme ("dark", "monokai")' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.o}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.t}</td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.d}</td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Request Body Inference */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Request Body Inference Strategies</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The generator uses four strategies to infer request bodies (in order of priority):
        </p>
        <div className="space-y-4">
          {[
            { num: '1', title: 'ParameterMetadata', desc: 'If route parameters have source="body", their types are used directly.', code: `@Post("/", request_serializer=CreateUserSerializer)\nasync def create(self, ctx):\n    data = ctx.validated_data  # Auto-populated by serializer` },
            { num: '2', title: 'Annotated[..., Body()]', desc: 'Python Annotated hints with Body() marker are detected.', code: `from typing import Annotated\nfrom aquilia import Body\n\n@Post("/")\nasync def create(self, ctx, data: Annotated[CreateUser, Body()]):\n    ...` },
            { num: '3', title: 'Docstring Body: {} Pattern', desc: 'Structured Body: {...} patterns in docstrings are parsed.', code: `@Post("/")\nasync def create(self, ctx):\n    """Create a user.\n\n    Body: {"name": "John", "age": 25, "active": true}\n    """\n    body = await ctx.json()` },
            { num: '4', title: 'Source Analysis', desc: 'If handler calls ctx.json() or ctx.form(), a generic body is inferred.', code: `@Post("/")\nasync def create(self, ctx):\n    body = await ctx.json()  # Inferred as application/json\n    # or\n    form = await ctx.form()  # Inferred as application/x-www-form-urlencoded` },
          ].map((item, i) => (
            <div key={i} className={boxClass}>
              <div className="flex items-start gap-3 mb-3">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-aquilia-500/20 text-aquilia-500 flex items-center justify-center text-sm font-bold">{item.num}</span>
                <div>
                  <h3 className={`font-bold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.title}</h3>
                  <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.desc}</p>
                </div>
              </div>
              <CodeBlock language="python">{item.code}</CodeBlock>
            </div>
          ))}
        </div>
      </section>

      {/* Security Scheme Detection */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Security Scheme Detection</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Pipeline guards are automatically mapped to OpenAPI security schemes based on their class names:
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Guard Pattern</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Security Scheme</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { guard: 'AuthGuard / Auth', scheme: 'Bearer (JWT) — http/bearer' },
                { guard: 'ApiKeyGuard', scheme: 'API Key — apiKey in header (X-API-Key)' },
                { guard: 'OAuthGuard', scheme: 'OAuth2 — authorization_code flow' },
                { guard: 'RoleGuard / ScopeGuard', scheme: 'Extends parent scheme with scopes/roles' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.guard}</code></td>
                  <td className={`py-3 px-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.scheme}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock language="python" filename="Security Detection">{`class AdminController(Controller):
    prefix = "/admin"
    pipeline = [Auth.guard()]  # → bearerAuth security scheme

    @Post("/users", pipeline=[Auth.guard(), RoleGuard("admin")])
    async def create(self, ctx):
        # OpenAPI will show: security: [{bearerAuth: ["admin"]}]
        ...`}</CodeBlock>
      </section>

      {/* Type Mapping */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Python → JSON Schema Mapping</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The generator maps Python type annotations to JSON Schema fragments automatically:
        </p>
        <div className={`overflow-hidden rounded-xl border ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-900' : 'bg-gray-50'}>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Python Type</th>
                <th className={`text-left py-3 px-4 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>JSON Schema</th>
              </tr>
            </thead>
            <tbody className={isDark ? 'divide-y divide-white/5' : 'divide-y divide-gray-100'}>
              {[
                { py: 'str', js: '{"type": "string"}' },
                { py: 'int', js: '{"type": "integer"}' },
                { py: 'float', js: '{"type": "number", "format": "double"}' },
                { py: 'bool', js: '{"type": "boolean"}' },
                { py: 'bytes', js: '{"type": "string", "format": "binary"}' },
                { py: 'Optional[X]', js: '{...X, "nullable": true}' },
                { py: 'List[X]', js: '{"type": "array", "items": X}' },
                { py: 'Dict[str, X]', js: '{"type": "object", "additionalProperties": X}' },
                { py: 'Tuple[A, B]', js: '{"type": "array", "prefixItems": [A, B]}' },
                { py: 'Set[X]', js: '{"type": "array", "uniqueItems": true}' },
                { py: '@dataclass MyModel', js: '{"$ref": "#/components/schemas/MyModel"}' },
              ].map((row, i) => (
                <tr key={i} className={isDark ? 'bg-[#0A0A0A]' : 'bg-white'}>
                  <td className="py-3 px-4"><code className="text-aquilia-500 font-mono text-xs">{row.py}</code></td>
                  <td className={`py-3 px-4 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{row.js}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Programmatic Usage */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Programmatic Usage</h2>
        <CodeBlock language="python" filename="Manual Generation">{`from aquilia.controller.openapi import OpenAPIGenerator, OpenAPIConfig

# Create the generator with configuration
generator = OpenAPIGenerator(config=OpenAPIConfig(
    title="My API",
    version="2.0.0",
    description="Comprehensive API documentation",
    detect_security=True,
    infer_request_body=True,
    infer_responses=True,
))

# Generate the spec from the router
spec = generator.generate(router)

# The spec is a plain dict — serialize as JSON or YAML
import json
json_spec = json.dumps(spec, indent=2)

# Access specific parts
print(spec["info"]["title"])           # "My API"
print(list(spec["paths"].keys()))      # ["/api/users/", "/api/users/{id}", ...]
print(spec["components"]["schemas"])   # {"UserModel": {...}, "ErrorResponse": {...}}`}</CodeBlock>
      </section>

      {/* Swagger UI / ReDoc */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Built-in UIs</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          When OpenAPI is enabled, Aquilia serves three endpoints:
        </p>
        <div className="space-y-3">
          {[
            { path: '/docs', desc: 'Swagger UI — interactive API explorer with "Try it out" functionality' },
            { path: '/redoc', desc: 'ReDoc — beautiful, responsive API documentation' },
            { path: '/openapi.json', desc: 'Raw OpenAPI 3.1.0 JSON specification' },
          ].map((endpoint, i) => (
            <div key={i} className={`${boxClass} flex items-center gap-4`}>
              <code className="text-aquilia-500 font-mono font-bold text-sm">{endpoint.path}</code>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{endpoint.desc}</p>
            </div>
          ))}
        </div>

        <div className={`mt-6 p-4 rounded-xl border flex items-start gap-3 ${isDark ? 'bg-blue-500/5 border-blue-500/20' : 'bg-blue-50 border-blue-200'}`}>
          <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <p className={`text-sm ${isDark ? 'text-blue-300' : 'text-blue-700'}`}>
            The generator also supports the <code className="font-mono">render_swagger_html()</code> and <code className="font-mono">render_redoc_html()</code> methods for embedding UI in custom templates with theme support.
          </p>
        </div>
      </section>

      {/* Navigation */}
      <div className={`flex items-center justify-between pt-8 mt-12 border-t ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
        <Link to="/docs/controllers/router" className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Controller Router
        </Link>
        <Link to="/docs/routing/overview" className="flex items-center gap-2 text-sm text-aquilia-500 font-semibold hover:text-aquilia-400">
          Routing <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
