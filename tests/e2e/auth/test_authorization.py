"""
E2E Auth Tests — Authorization (RBAC, ABAC, Scopes, Tenants)

Tests the authorization engine with RBAC, ABAC policies, scope checking,
tenant isolation, and policy builders.
"""

import pytest

from aquilia.auth.core import Identity, IdentityType, IdentityStatus
from aquilia.auth.authz import (
    AuthzEngine,
    RBACEngine,
    ABACEngine,
    AuthzContext,
    Decision,
    AuthzResult,
    ScopeChecker,
    PolicyBuilder,
)
from aquilia.auth.faults import (
    AUTHZ_INSUFFICIENT_SCOPE,
    AUTHZ_INSUFFICIENT_ROLE,
    AUTHZ_RESOURCE_FORBIDDEN,
    AUTHZ_TENANT_MISMATCH,
    AUTHZ_POLICY_DENIED,
)


def _make_context(
    identity_id="user-001",
    resource="orders:123",
    action="read",
    scopes=None,
    roles=None,
    tenant_id=None,
    attributes=None,
):
    """Build an AuthzContext with defaults."""
    identity = Identity(
        id=identity_id,
        type=IdentityType.USER,
        attributes={"roles": roles or [], "scopes": scopes or []},
        status=IdentityStatus.ACTIVE,
        tenant_id=tenant_id,
    )
    return AuthzContext(
        identity=identity,
        resource=resource,
        action=action,
        scopes=scopes or [],
        roles=roles or [],
        tenant_id=tenant_id,
        attributes=attributes or {},
    )


class TestRBAC:
    """Role-Based Access Control tests."""

    def test_rbac_permission_check_allowed(self, rbac_engine):
        """Role with permission passes check."""
        context = _make_context(roles=["editor"])
        result = rbac_engine.check(context, "write")
        assert result.decision == Decision.ALLOW

    def test_rbac_permission_check_denied(self, rbac_engine):
        """Role without permission is denied."""
        context = _make_context(roles=["viewer"])
        result = rbac_engine.check(context, "delete")
        assert result.decision == Decision.DENY

    def test_rbac_inheritance(self, rbac_engine):
        """Child role inherits parent permissions."""
        # Editor inherits from viewer (read), plus has write
        context = _make_context(roles=["editor"])
        result_read = rbac_engine.check(context, "read")
        result_write = rbac_engine.check(context, "write")
        assert result_read.decision == Decision.ALLOW
        assert result_write.decision == Decision.ALLOW

    def test_rbac_admin_has_all(self, rbac_engine):
        """Admin role has all permissions via inheritance chain."""
        context = _make_context(roles=["admin"])
        for perm in ["read", "write", "delete", "admin"]:
            result = rbac_engine.check(context, perm)
            assert result.decision == Decision.ALLOW, f"Admin should have {perm}"


class TestScopeChecker:
    """OAuth2-style scope checking."""

    def test_scope_checker_satisfied(self):
        """All required scopes available → allow."""
        result = ScopeChecker.check(
            _make_context(scopes=["read", "write", "admin"]),
            required_scopes=["read", "write"],
        )
        assert result.decision == Decision.ALLOW

    def test_scope_checker_missing(self):
        """Missing scopes → deny."""
        result = ScopeChecker.check(
            _make_context(scopes=["read"]),
            required_scopes=["read", "write"],
        )
        assert result.decision == Decision.DENY

    def test_scope_checker_empty_required(self):
        """Empty required scopes → allow (no requirements)."""
        result = ScopeChecker.check(
            _make_context(scopes=["read"]),
            required_scopes=[],
        )
        assert result.decision == Decision.ALLOW


class TestABACPolicies:
    """Attribute-Based Access Control tests."""

    def test_abac_custom_policy(self, abac_engine):
        """Custom policy function evaluated correctly."""
        def ip_policy(ctx: AuthzContext) -> AuthzResult:
            ip = ctx.attributes.get("client_ip", "")
            if ip.startswith("10."):
                return AuthzResult(decision=Decision.ALLOW, reason="Internal IP")
            return AuthzResult(decision=Decision.DENY, reason="External IP")

        abac_engine.register_policy("ip-check", ip_policy)

        ctx_internal = _make_context(attributes={"client_ip": "10.0.0.1"})
        assert abac_engine.evaluate(ctx_internal, "ip-check").decision == Decision.ALLOW

        ctx_external = _make_context(attributes={"client_ip": "203.0.113.1"})
        assert abac_engine.evaluate(ctx_external, "ip-check").decision == Decision.DENY

    def test_abac_missing_policy_abstains(self, abac_engine):
        """Non-existent policy returns ABSTAIN."""
        ctx = _make_context()
        result = abac_engine.evaluate(ctx, "nonexistent-policy")
        assert result.decision == Decision.ABSTAIN


class TestAuthzEngine:
    """Unified AuthzEngine tests."""

    def test_scope_check_raises_on_missing(self, authz_engine):
        """`check_scope` raises AUTHZ_INSUFFICIENT_SCOPE on failure."""
        ctx = _make_context(scopes=["read"])
        with pytest.raises(AUTHZ_INSUFFICIENT_SCOPE):
            authz_engine.check_scope(ctx, ["read", "admin"])

    def test_scope_check_passes(self, authz_engine):
        """`check_scope` passes when all scopes present."""
        ctx = _make_context(scopes=["read", "write"])
        authz_engine.check_scope(ctx, ["read", "write"])  # Should not raise

    def test_role_check_raises_on_missing(self, authz_engine):
        """`check_role` raises AUTHZ_INSUFFICIENT_ROLE on failure."""
        ctx = _make_context(roles=["viewer"])
        with pytest.raises(AUTHZ_INSUFFICIENT_ROLE):
            authz_engine.check_role(ctx, ["admin"])

    def test_role_check_passes(self, authz_engine):
        """`check_role` passes when user has any required role."""
        ctx = _make_context(roles=["editor", "viewer"])
        authz_engine.check_role(ctx, ["editor"])  # Should not raise

    def test_permission_check_raises(self, authz_engine):
        """`check_permission` raises AUTHZ_RESOURCE_FORBIDDEN on failure."""
        ctx = _make_context(roles=["viewer"])
        with pytest.raises(AUTHZ_RESOURCE_FORBIDDEN):
            authz_engine.check_permission(ctx, "delete")

    def test_default_deny_when_no_policies(self, authz_engine):
        """No matching policy → default deny."""
        ctx = _make_context(roles=["viewer"])
        result = authz_engine.check(ctx)
        assert result.decision == Decision.DENY
        assert "default deny" in result.reason.lower()


class TestTenantIsolation:
    """Multi-tenant access control."""

    def test_tenant_isolation_mismatch(self, authz_engine):
        """Cross-tenant access raises AUTHZ_TENANT_MISMATCH."""
        ctx = _make_context(tenant_id="tenant-A")
        with pytest.raises(AUTHZ_TENANT_MISMATCH):
            authz_engine.check_tenant(ctx, "tenant-B")

    def test_tenant_isolation_match(self, authz_engine):
        """Same-tenant access passes."""
        ctx = _make_context(tenant_id="tenant-A")
        authz_engine.check_tenant(ctx, "tenant-A")  # Should not raise


class TestPolicyBuilders:
    """Pre-built policy patterns."""

    def test_owner_only_policy(self):
        """owner_only policy allows owner, denies others."""
        policy = PolicyBuilder.owner_only()

        # Owner access
        ctx_owner = _make_context(
            identity_id="user-001",
            attributes={"owner_id": "user-001"},
        )
        assert policy(ctx_owner).decision == Decision.ALLOW

        # Non-owner access
        ctx_other = _make_context(
            identity_id="user-002",
            attributes={"owner_id": "user-001"},
        )
        assert policy(ctx_other).decision == Decision.DENY

    def test_admin_or_owner_policy(self):
        """admin_or_owner policy allows admin or resource owner."""
        policy = PolicyBuilder.admin_or_owner()

        # Admin (not owner)
        ctx_admin = _make_context(
            identity_id="admin-001",
            roles=["admin"],
            attributes={"owner_id": "user-001"},
        )
        assert policy(ctx_admin).decision == Decision.ALLOW

        # Owner (not admin)
        ctx_owner = _make_context(
            identity_id="user-001",
            roles=["user"],
            attributes={"owner_id": "user-001"},
        )
        assert policy(ctx_owner).decision == Decision.ALLOW

        # Neither admin nor owner
        ctx_other = _make_context(
            identity_id="user-002",
            roles=["user"],
            attributes={"owner_id": "user-001"},
        )
        assert policy(ctx_other).decision == Decision.DENY
