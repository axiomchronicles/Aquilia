import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { FileText, Layers, Zap, Code, Shield, Settings, ArrowRight, Globe } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function ControllersOpenAPI() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-aquilia-500/30 to-aquilia-500/10 flex items-center justify-center">
            <FileText className="w-5 h-5 text-aquilia-400" />
          </div>
          <div>
            <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
              <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
                OpenAPI Generation
                <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
              </span>
            </h1>
            <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>aquilia.controller.openapi — OpenAPI 3.1.0 spec from controller metadata</p>
          </div>
        </div>

        <p className={`text-lg ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia automatically generates a complete <strong>OpenAPI 3.1.0</strong> specification
          from compiled controller routes. The generator introspects decorators, type hints,
          docstrings, and source code to produce paths, parameters, request bodies, responses,
          security schemes, and component schemas — with Swagger UI and ReDoc rendering built-in.
        </p>
      </div>

      {/* OpenAPIConfig */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Settings className="w-5 h-5 text-aquilia-400" />
          OpenAPIConfig
        </h2>

        <CodeBlock
          code={`@dataclass
class OpenAPIConfig:
    # ── Info ──────────────────────────────────────────────────
    title: str = "Aquilia API"
    version: str = "1.0.0"
    description: str = ""
    terms_of_service: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_url: str = ""
    license_name: str = ""
    license_url: str = ""

    # ── Servers ───────────────────────────────────────────────
    servers: List[Dict[str, str]] = field(default_factory=list)

    # ── Paths ─────────────────────────────────────────────────
    docs_path: str = "/docs"              # Swagger UI path
    openapi_json_path: str = "/openapi.json"  # JSON spec path
    redoc_path: str = "/redoc"            # ReDoc path

    # ── Features ──────────────────────────────────────────────
    include_internal: bool = False        # Include /_internal routes
    group_by_module: bool = True          # Group tags by module
    infer_request_body: bool = True       # Auto-detect request bodies
    infer_responses: bool = True          # Auto-detect response schemas
    detect_security: bool = True          # Detect auth from pipeline guards

    # ── External Docs ─────────────────────────────────────────
    external_docs_url: str = ""
    external_docs_description: str = ""

    # ── Swagger UI ────────────────────────────────────────────
    swagger_ui_theme: str = ""            # "", "dark", "monokai"
    swagger_ui_config: Dict[str, Any] = field(default_factory=dict)

    # ── Enabled ───────────────────────────────────────────────
    enabled: bool = True`}
          language="python"
        />

        <p className={`mt-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Configuration can be set via <code>Integration.openapi(...)</code> in
          <code>workspace.py</code> or passed directly to the generator:
        </p>

        <CodeBlock
          code={`# In workspace.py:
from aquilia.config_builders import Workspace, Integration

workspace = (
    Workspace("my_api")
    .integrate(
        Integration.openapi(
            title="My API",
            version="2.0.0",
            description="Production API",
            docs_path="/api/docs",
            swagger_ui_theme="dark",
            detect_security=True,
        )
    )
)`}
          language="python"
        />
      </section>

      {/* OpenAPIGenerator */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Code className="w-5 h-5 text-aquilia-400" />
          OpenAPIGenerator
        </h2>

        <CodeBlock
          code={`class OpenAPIGenerator:
    def __init__(
        self,
        title: str = "Aquilia API",
        version: str = "1.0.0",
        config: Optional[OpenAPIConfig] = None,
    ):
        if config:
            self.config = config
        else:
            self.config = OpenAPIConfig(title=title, version=version)

    def generate(self, router: ControllerRouter) -> Dict[str, Any]:
        """Generate the full OpenAPI 3.1.0 specification."""
        # Returns a complete spec dict with:
        # - openapi: "3.1.0"
        # - info: title, version, description, contact, license
        # - servers: list of server URLs
        # - paths: all routes with operations
        # - tags: controller-derived tags
        # - components: schemas + securitySchemes + ErrorResponse`}
          language="python"
        />
      </section>

      {/* Spec generation features */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Layers className="w-5 h-5 text-aquilia-400" />
          What Gets Generated
        </h2>

        <div className={`space-y-3`}>
          {[
            { title: 'Path & Query Parameters', desc: 'Extracted from CompiledPattern — path params get {name} OpenAPI syntax, query params are listed with types from pattern castors. Docstring descriptions are merged in.' },
            { title: 'Request Body Inference (4 strategies)', desc: '(1) ParameterMetadata with source="body", (2) Annotated[T, Body(...)] in handler signature, (3) Body: {...} pattern in docstrings, (4) Source code analysis for ctx.json() or ctx.form() calls.' },
            { title: 'Response Schema', desc: 'From response_model type annotation → $ref to components/schemas. Inferred from source: Response.json() → object, Response.html()/self.render() → text/html, Response.text() → text/plain.' },
            { title: 'Error Responses', desc: 'From docstring Raises: sections and source code analysis of status_NNN patterns. Standard ErrorResponse schema is always included in components.' },
            { title: 'Security Schemes', desc: 'Auto-detected from pipeline guard class names: "oauth" → OAuth2, "apikey" → API Key header, "authguard"/"auth" → Bearer JWT. Scopes extracted from ScopeGuard/RoleGuard nodes.' },
            { title: 'Tags', desc: 'From controller.tags → route.tags → controller class name (sans "Controller" suffix). Controller docstrings become tag descriptions.' },
            { title: 'Component Schemas', desc: 'response_model classes with __annotations__ are converted to JSON Schema objects with $ref deduplication.' },
          ].map(({ title, desc }, i) => (
            <div key={i} className={`rounded-xl border p-4 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
              <h4 className={`font-semibold text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>{title}</h4>
              <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Type mapping */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Zap className="w-5 h-5 text-aquilia-400" />
          Python → JSON Schema Mapping
        </h2>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Python Type</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>JSON Schema</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['str', '{"type": "string"}'],
                ['int', '{"type": "integer"}'],
                ['float', '{"type": "number", "format": "double"}'],
                ['bool', '{"type": "boolean"}'],
                ['bytes', '{"type": "string", "format": "binary"}'],
                ['None', '{"type": "null"}'],
                ['Optional[X]', '{...X schema..., "nullable": true}'],
                ['Union[A, B]', '{"anyOf": [{A schema}, {B schema}]}'],
                ['List[X]', '{"type": "array", "items": {X schema}}'],
                ['Dict[str, X]', '{"type": "object", "additionalProperties": {X schema}}'],
                ['Tuple[A, B]', '{"type": "array", "prefixItems": [...], "minItems": 2, "maxItems": 2}'],
                ['Set[X]', '{"type": "array", "items": {X schema}, "uniqueItems": true}'],
                ['@dataclass / class', '{"$ref": "#/components/schemas/ClassName"}'],
              ].map(([python, json], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{python}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{json}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Security detection */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Shield className="w-5 h-5 text-aquilia-400" />
          Security Scheme Detection
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The generator inspects pipeline guard class names to automatically detect
          security schemes:
        </p>

        <div className={`rounded-xl border overflow-hidden ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className={isDark ? 'bg-zinc-800/80' : 'bg-gray-50'}>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Guard Class Contains</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Security Scheme</th>
                <th className={`text-left px-4 py-3 font-semibold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Details</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {[
                ['"oauth"', 'oauth2', 'Authorization code flow with /auth/authorize and /auth/token'],
                ['"apikey"', 'apiKeyAuth', 'API Key in X-API-Key header'],
                ['"authguard" or "auth"', 'bearerAuth', 'HTTP Bearer with JWT format'],
                ['"scope" or "role"', '(extends last)', 'Extracts scopes/roles from .scopes or .roles attributes'],
              ].map(([contains, scheme, details], i) => (
                <tr key={i} className={isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'}>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-aquilia-400' : 'text-aquilia-600'}`}>{contains}</td>
                  <td className={`px-4 py-2 font-mono text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{scheme}</td>
                  <td className={`px-4 py-2 text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Swagger UI & ReDoc */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <Globe className="w-5 h-5 text-aquilia-400" />
          Swagger UI & ReDoc
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          Aquilia generates HTML pages for both Swagger UI (v5.18.2) and ReDoc:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>Swagger UI</h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              <li>• Default path: <code>/docs</code></li>
              <li>• Interactive "Try it out" enabled</li>
              <li>• Deep linking support</li>
              <li>• Dark theme available</li>
              <li>• Configurable via <code>swagger_ui_config</code></li>
              <li>• Generated by <code>generate_swagger_html(config)</code></li>
            </ul>
          </div>

          <div className={`rounded-xl border p-5 ${isDark ? 'bg-zinc-900/50 border-white/10' : 'bg-gray-50 border-gray-200'}`}>
            <h3 className={`font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>ReDoc</h3>
            <ul className={`text-sm space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              <li>• Default path: <code>/redoc</code></li>
              <li>• Clean, documentation-focused layout</li>
              <li>• Three-panel view</li>
              <li>• Auto-expands 200/201 responses</li>
              <li>• Path shown in middle panel</li>
              <li>• Generated by <code>generate_redoc_html(config)</code></li>
            </ul>
          </div>
        </div>

        <CodeBlock
          code={`# Accessing the docs (when server is running):
# Swagger UI:  http://localhost:8000/docs
# ReDoc:       http://localhost:8000/redoc
# JSON spec:   http://localhost:8000/openapi.json

# With custom paths:
# config = OpenAPIConfig(
#     docs_path="/api/docs",
#     redoc_path="/api/redoc",
#     openapi_json_path="/api/openapi.json",
# )`}
          language="python"
        />
      </section>

      {/* Docstring parsing */}
      <section className="mb-10">
        <h2 className={`text-2xl font-bold mb-4 flex items-center gap-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <ArrowRight className="w-5 h-5 text-aquilia-400" />
          Docstring Parsing
        </h2>

        <p className={`mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
          The generator parses handler docstrings to extract structured metadata:
        </p>

        <CodeBlock
          code={`@POST("/users", status_code=201)
async def create_user(self, ctx: RequestCtx) -> Response:
    """
    Create a new user account.

    Creates a user with the provided information and sends
    a verification email.

    Args:
        name: The user's full name
        email: The user's email address
        role: User role (admin, user, viewer)

    Body: {"name": "John", "email": "john@example.com", "role": "user"}

    Returns:
        The created user object with ID

    Raises:
        ValidationError (422): Invalid input data
        ConflictError (409): Email already registered
    """
    ...

# The generator extracts:
# - summary: "Create a new user account."
# - description: "Creates a user with the provided..."
# - params: {name: "...", email: "...", role: "..."}
# - request_body: inferred from Body: {...} pattern
# - returns: "The created user object with ID"
# - raises: [{exception: "ValidationError", status: "422", ...}, ...]`}
          language="python"
        />
      </section>

      {/* Navigation */}
      <section className="mb-10">
        <div className="flex justify-between">
          <Link to="/docs/controllers/router" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            ← ControllerRouter
          </Link>
          <Link to="/docs/config/overview" className={`text-sm font-medium ${isDark ? 'text-aquilia-400 hover:text-aquilia-300' : 'text-aquilia-600 hover:text-aquilia-500'}`}>
            Configuration →
          </Link>
        </div>
      </section>
    
      <NextSteps />
    </div>
  )
}