import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Shield } from 'lucide-react'
import { NextSteps } from '../../../components/NextSteps'

export function AuthGuards() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4"><Shield className="w-4 h-4" />Security &amp; Auth</div>
        <h1 className={`text-4xl ${isDark ? 'text-white' : 'text-gray-900'}`}>
          <span className="font-bold tracking-tighter gradient-text font-mono relative group inline-block">
            Guards
            <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-gradient-to-r from-aquilia-500 to-aquilia-400 group-hover:w-full transition-all duration-300" />
          </span>
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Guards are policy functions that run before a controller method. They check the <code className="text-aquilia-500">Identity</code> and decide whether to allow or deny the request. Integrate with controller pipelines for composable security.
        </p>
      </div>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Writing a Guard</h2>
        <CodeBlock language="python" filename="Custom Guard">{`from aquilia.response import Response

# A guard is any async callable that takes RequestCtx
# and returns None (allow) or a Response (deny)

async def require_auth(ctx):
    """Deny if no identity or not active."""
    if not ctx.identity or not ctx.identity.is_active():
        return Response.json({"error": "Unauthorized"}, status=401)
    return None  # Allow

async def require_role(*roles):
    """Factory that creates a guard for specific roles."""
    async def guard(ctx):
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)
        for role in roles:
            if ctx.identity.has_role(role):
                return None  # Allow
        return Response.json({"error": "Forbidden"}, status=403)
    return guard

async def require_scope(scope: str):
    """Deny if identity lacks the required scope."""
    async def guard(ctx):
        if not ctx.identity or not ctx.identity.has_scope(scope):
            return Response.json({"error": "Insufficient scope"}, status=403)
        return None
    return guard`}</CodeBlock>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Using Guards in Controllers</h2>
        <CodeBlock language="python" filename="Controller Pipeline">{`from aquilia.controller import Controller, Get, Post

class AdminController(Controller):
    prefix = "/admin"
    pipeline = [require_auth, require_role("admin")]  # Controller-level

    @Get("/dashboard")
    async def dashboard(self, ctx):
        return ctx.json({"message": "Admin dashboard"})

    @Post("/users", pipeline=[require_scope("write:users")])  # Route-level
    async def create_user(self, ctx):
        data = await ctx.request.json()
        return ctx.json({"created": True})`}</CodeBlock>
        <div className={`mt-4 p-4 rounded-xl border-l-4 border-aquilia-500 ${isDark ? 'bg-aquilia-500/10' : 'bg-aquilia-50'}`}>
          <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            <strong>Pipeline execution order:</strong> Controller pipeline runs first, then route-level pipeline. If any guard returns a Response, execution stops and that response is sent.
          </p>
        </div>
      </section>

      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Tenant Isolation</h2>
        <CodeBlock language="python" filename="Tenant Guard">{`async def require_tenant(ctx):
    """Ensure identity belongs to a tenant."""
    if not ctx.identity or not ctx.identity.tenant_id:
        return Response.json({"error": "Tenant required"}, status=403)
    
    # Make tenant_id available to downstream services
    ctx.state["tenant_id"] = ctx.identity.tenant_id
    return None

class TenantController(Controller):
    prefix = "/api"
    pipeline = [require_auth, require_tenant]

    @Get("/data")
    async def get_data(self, ctx):
        tenant = ctx.state["tenant_id"]
        data = await self.service.list_for_tenant(tenant)
        return ctx.json(data)`}</CodeBlock>
      </section>
    
      <NextSteps />
    </div>
  )
}