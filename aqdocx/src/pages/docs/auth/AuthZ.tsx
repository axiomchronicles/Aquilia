import { useTheme } from '../../../context/ThemeContext'
import { CodeBlock } from '../../../components/CodeBlock'
import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Lock } from 'lucide-react'

export function AuthZPage() {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-12">
        <div className="flex items-center gap-2 text-sm text-aquilia-500 font-medium mb-4">
          <Lock className="w-4 h-4" />
          Security / Authorization
        </div>
        <h1 className={`text-4xl font-extrabold tracking-tight mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
          Authorization
        </h1>
        <p className={`text-lg leading-relaxed ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          Aquilia provides multiple authorization engines — RBAC, ABAC, and a Policy DSL — that integrate directly with guards, middleware, and the DI system. Default-deny ensures secure-by-default access control.
        </p>
      </div>

      {/* RBAC */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Role-Based Access Control (RBAC)</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">RBACEngine</code> checks permissions based on assigned roles. Roles map to sets of permissions.
        </p>
        <CodeBlock language="python" filename="rbac.py">{`from aquilia.auth.authz import RBACEngine

rbac = RBACEngine()

# Define roles with permissions
rbac.define_role("admin", permissions=[
    "articles:read", "articles:write", "articles:delete",
    "users:read", "users:write", "users:delete",
    "settings:manage",
])

rbac.define_role("editor", permissions=[
    "articles:read", "articles:write",
    "users:read",
])

rbac.define_role("viewer", permissions=[
    "articles:read",
    "users:read",
])

# Role inheritance
rbac.define_role("super_admin", inherits=["admin"], permissions=[
    "system:shutdown",
    "system:audit",
])

# Check permissions
allowed = await rbac.check(
    identity=current_identity,
    permission="articles:write",
)
# → True if identity has "admin" or "editor" role`}</CodeBlock>

        <CodeBlock language="python" filename="rbac_guard.py">{`from aquilia import Controller, Get, Delete
from aquilia.auth import requires_role, requires_permission


class AdminController(Controller):
    prefix = "/admin"

    @Get("/dashboard")
    @requires_role("admin")
    async def dashboard(self, ctx):
        """Only admin role can access."""
        ...

    @Delete("/users/{id:int}")
    @requires_permission("users:delete")
    async def delete_user(self, ctx, id: int):
        """Any role with users:delete permission."""
        ...`}</CodeBlock>
      </section>

      {/* ABAC */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Attribute-Based Access Control (ABAC)</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The <code className="text-aquilia-500">ABACEngine</code> evaluates access based on attributes of the subject, resource, action, and environment.
        </p>
        <CodeBlock language="python" filename="abac.py">{`from aquilia.auth.authz import ABACEngine

abac = ABACEngine()

# Define attribute-based rules
abac.add_rule(
    name="owner_can_edit",
    condition=lambda subject, resource, action, env: (
        action == "edit"
        and resource.owner_id == subject.id
    ),
)

abac.add_rule(
    name="business_hours_only",
    condition=lambda subject, resource, action, env: (
        action in ("write", "delete")
        and 9 <= env.current_hour <= 17
        and env.day_of_week < 5  # Monday-Friday
    ),
)

abac.add_rule(
    name="department_access",
    condition=lambda subject, resource, action, env: (
        resource.department in subject.departments
    ),
)

# Evaluate
allowed = await abac.check(
    subject=current_identity,
    resource=article,
    action="edit",
    environment=request_context,
)`}</CodeBlock>
      </section>

      {/* Policy DSL */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Policy DSL</h2>
        <p className={`mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          The Policy DSL lets you compose fine-grained authorization rules with <code className="text-aquilia-500">Allow</code>, <code className="text-aquilia-500">Deny</code>, and <code className="text-aquilia-500">Abstain</code> decisions.
        </p>
        <CodeBlock language="python" filename="policy.py">{`from aquilia.auth.policy import (
    Policy, PolicyRegistry, PolicyDecision,
    Allow, Deny, Abstain, rule,
)


class ArticlePolicy(Policy):
    """Authorization rules for Article resources."""

    @rule
    async def owner_can_manage(self, identity, article, action):
        """Owners can do anything with their articles."""
        if article.author_id == identity.id:
            return Allow(reason="Owner has full access")
        return Abstain()

    @rule
    async def editors_can_edit(self, identity, article, action):
        """Editors can edit but not delete."""
        if "editor" in identity.roles and action != "delete":
            return Allow(reason="Editor access")
        return Abstain()

    @rule
    async def deny_suspended(self, identity, article, action):
        """Suspended users cannot perform any action."""
        if identity.status == "suspended":
            return Deny(reason="Account suspended")
        return Abstain()

    @rule
    async def deny_draft_from_viewers(self, identity, article, action):
        """Viewers cannot see draft articles."""
        if article.status == "draft" and "viewer" in identity.roles:
            return Deny(reason="Draft not visible to viewers")
        return Abstain()


# Register and use
registry = PolicyRegistry()
registry.register(ArticlePolicy)

result = await registry.evaluate(
    policy_class=ArticlePolicy,
    identity=current_user,
    resource=article,
    action="edit",
)

if result.decision == PolicyDecision.ALLOW:
    # proceed
    pass
elif result.decision == PolicyDecision.DENY:
    # 403 Forbidden
    raise AUTHZ_POLICY_DENIED(reason=result.reason)`}</CodeBlock>
      </section>

      {/* Guard Integration */}
      <section className="mb-16">
        <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>Guard Integration</h2>
        <CodeBlock language="python" filename="guards.py">{`from aquilia import Controller, Get, Put, Delete
from aquilia.auth import AuthGuard, PolicyGuard, ScopeGuard


class ArticleController(Controller):
    prefix = "/api/articles"

    @Get("/")
    async def list_articles(self, ctx):
        """Public — no guard required."""
        ...

    @Get("/{id:int}")
    @AuthGuard()  # Must be authenticated
    async def get_article(self, ctx, id: int):
        ...

    @Put("/{id:int}")
    @PolicyGuard(ArticlePolicy, action="edit")
    async def update_article(self, ctx, id: int):
        """Evaluated against ArticlePolicy rules."""
        ...

    @Delete("/{id:int}")
    @ScopeGuard("articles:delete")
    async def delete_article(self, ctx, id: int):
        """Requires articles:delete scope in token."""
        ...`}</CodeBlock>
      </section>

      {/* Nav */}
      <div className="flex justify-between items-center mt-16 pt-8 border-t border-white/10">
        <Link to="/docs/auth" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          <ArrowLeft className="w-4 h-4" /> Authentication
        </Link>
        <Link to="/docs/sessions" className="flex items-center gap-2 text-aquilia-500 hover:text-aquilia-400 transition">
          Sessions <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
