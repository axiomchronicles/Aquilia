import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, AlertTriangle } from 'lucide-react'

export function FaultsAdvanced() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <AlertTriangle className="w-4 h-4" />
          Faults / Handlers & Domains
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Fault Handlers & Domains
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia's fault system goes beyond simple exception handling. Fault handlers let you customize error responses, while fault domains organize errors by subsystem for better diagnostics and recovery.
        </p>
      </div>

      {/* Fault Handlers */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Custom Fault Handlers</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Register handlers that intercept specific fault types and produce custom responses.
        </p>
        <CodeBlock language="python" filename="handlers.py">{`from aquilia.faults import FaultEngine, AquiliaFault, FaultHandler


class ValidationFaultHandler(FaultHandler):
    """Custom handler for validation errors."""

    def can_handle(self, fault: AquiliaFault) -> bool:
        return fault.domain == "validation"

    async def handle(self, fault: AquiliaFault, ctx):
        return ctx.json({
            "error": "Validation Error",
            "code": fault.code,
            "details": fault.details,
            "fields": fault.metadata.get("fields", {}),
        }, status=422)


class NotFoundFaultHandler(FaultHandler):
    """Custom 404 handler."""

    def can_handle(self, fault: AquiliaFault) -> bool:
        return fault.status == 404

    async def handle(self, fault: AquiliaFault, ctx):
        accept = ctx.request.headers.get("accept", "")

        if "text/html" in accept:
            # Render custom 404 page
            return ctx.render("errors/404.html", {
                "path": ctx.request.path,
            })

        return ctx.json({
            "error": "Not Found",
            "path": ctx.request.path,
            "suggestion": f"Did you mean /api{ctx.request.path}?",
        }, status=404)


# Register handlers
engine = FaultEngine()
engine.add_handler(ValidationFaultHandler())
engine.add_handler(NotFoundFaultHandler())`}</CodeBlock>
      </section>

      {/* Handler Priority */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Handler Priority</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Handlers are evaluated in registration order. The first handler that returns <code className="text-aquilia-500">True</code> from <code className="text-aquilia-500">can_handle()</code> wins. Use priority to control ordering.
        </p>
        <CodeBlock language="python" filename="priority.py">{`engine.add_handler(ValidationFaultHandler(), priority=100)  # Highest
engine.add_handler(NotFoundFaultHandler(), priority=50)
engine.add_handler(DefaultFaultHandler(), priority=0)       # Fallback

# For a validation fault:
# 1. ValidationFaultHandler.can_handle() → True → handles it
# 2. NotFoundFaultHandler.can_handle() → never reached

# For a 404 fault:
# 1. ValidationFaultHandler.can_handle() → False
# 2. NotFoundFaultHandler.can_handle() → True → handles it`}</CodeBlock>
      </section>

      {/* Fault Domains */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Fault Domains</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Fault domains organize errors by subsystem. Each domain has its own fault codes, metadata schema, and recovery strategies.
        </p>
        <CodeBlock language="python" filename="domains.py">{`from aquilia.faults import fault, FaultDomain

# Define domain
auth_domain = FaultDomain(
    name="auth",
    prefix="AUTH",          # Fault codes: AUTH_001, AUTH_002, ...
    default_status=401,
)

db_domain = FaultDomain(
    name="database",
    prefix="DB",
    default_status=500,
)

validation_domain = FaultDomain(
    name="validation",
    prefix="VAL",
    default_status=422,
)

# Define faults within domains
AUTH_INVALID_CREDENTIALS = fault(
    domain=auth_domain,
    code="AUTH_001",
    message="Invalid credentials",
    status=401,
)

AUTH_TOKEN_EXPIRED = fault(
    domain=auth_domain,
    code="AUTH_002",
    message="Token has expired",
    status=401,
    metadata_schema={"expired_at": "datetime"},
)

DB_CONNECTION_FAILED = fault(
    domain=db_domain,
    code="DB_001",
    message="Database connection failed",
    status=503,
    retry_after=30,  # Suggest retry
)

VAL_FIELD_REQUIRED = fault(
    domain=validation_domain,
    code="VAL_001",
    message="Required field is missing",
    status=422,
)`}</CodeBlock>
      </section>

      {/* Raising Faults */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Raising Faults</h2>
        <CodeBlock language="python" filename="raising.py">{`# Raise a domain fault
raise AUTH_INVALID_CREDENTIALS()

# With additional context
raise AUTH_TOKEN_EXPIRED(
    metadata={"expired_at": "2025-01-15T12:00:00Z"},
    details="Token expired 2 hours ago",
)

# With field-level errors
raise VAL_FIELD_REQUIRED(
    metadata={
        "fields": {
            "email": "This field is required",
            "name": "This field is required",
        }
    }
)

# Conditional fault
user = await User.objects.get_or_none(id=user_id)
if not user:
    raise fault(
        code="USER_NOT_FOUND",
        message=f"User {user_id} not found",
        status=404,
        domain="users",
    )`}</CodeBlock>
      </section>

      {/* Debug Pages */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Debug Error Pages</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          In development mode, Aquilia renders beautiful error pages with full tracebacks, source code context, local variables, and request inspection.
        </p>
        <CodeBlock language="python" filename="debug.py">{`from aquilia.debug import render_debug_exception_page, DebugPageRenderer

# Automatic in development mode (DEBUG=True)
# Unhandled exceptions render as interactive debug pages with:
# - Full traceback with syntax-highlighted source code
# - Local variables per stack frame
# - Request headers, cookies, query params, body
# - Dark/light mode toggle

# Custom debug renderer
renderer = DebugPageRenderer(
    show_locals=True,          # Show local variables
    context_lines=7,           # Lines of source context
    enable_console=False,      # Interactive console (security risk)
)

# Styled HTTP error pages (400, 401, 403, 404, 405, 500)
from aquilia.debug import render_http_error_page
page = render_http_error_page(status=404, path="/missing")`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/faults/engine" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Fault Engine
        </Link>
        <Link to="/docs/cache" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          Cache <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
