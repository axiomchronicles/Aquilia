"""
AquilAuth - Authorization Engine

RBAC, ABAC, and policy-based authorization engine.
Supports AquilaPolicy DSL for declarative access control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .core import Identity
from .faults import (
    AUTHZ_INSUFFICIENT_ROLE,
    AUTHZ_INSUFFICIENT_SCOPE,
    AUTHZ_POLICY_DENIED,
    AUTHZ_RESOURCE_FORBIDDEN,
    AUTHZ_TENANT_MISMATCH,
)


# ============================================================================
# Authorization Types
# ============================================================================


class Decision(str, Enum):
    """Authorization decision."""

    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"  # No decision (defer to next policy)


@dataclass
class AuthzContext:
    """Authorization context for policy evaluation."""

    identity: Identity
    resource: str  # Resource identifier (e.g., "orders:123")
    action: str  # Action (e.g., "read", "write", "delete")
    scopes: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthzResult:
    """Authorization result."""

    decision: Decision
    reason: str | None = None
    policy_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# RBAC (Role-Based Access Control)
# ============================================================================


class RBACEngine:
    """
    Role-Based Access Control engine.

    Defines roles and their permissions.
    """

    def __init__(self):
        self._roles: dict[str, set[str]] = {}  # role -> permissions
        self._role_hierarchy: dict[str, set[str]] = {}  # role -> parent roles

    def define_role(
        self, role: str, permissions: list[str], inherits: list[str] | None = None
    ) -> None:
        """
        Define role with permissions and inheritance.

        Args:
            role: Role name
            permissions: List of permissions
            inherits: Parent roles to inherit from
        """
        self._roles[role] = set(permissions)

        if inherits:
            self._role_hierarchy[role] = set(inherits)

    def get_permissions(self, role: str) -> set[str]:
        """
        Get all permissions for role (including inherited).

        Args:
            role: Role name

        Returns:
            Set of permissions
        """
        permissions = set(self._roles.get(role, set()))

        # Add inherited permissions
        if role in self._role_hierarchy:
            for parent_role in self._role_hierarchy[role]:
                permissions.update(self.get_permissions(parent_role))

        return permissions

    def check_permission(
        self, roles: list[str], permission: str
    ) -> bool:
        """
        Check if any role has permission.

        Args:
            roles: List of roles
            permission: Permission to check

        Returns:
            True if any role has permission
        """
        for role in roles:
            if permission in self.get_permissions(role):
                return True

        return False

    def check(self, context: AuthzContext, permission: str) -> AuthzResult:
        """
        Check authorization using RBAC.

        Args:
            context: Authorization context
            permission: Required permission

        Returns:
            Authorization result
        """
        if self.check_permission(context.roles, permission):
            return AuthzResult(
                decision=Decision.ALLOW,
                reason=f"Role has permission: {permission}",
            )

        return AuthzResult(
            decision=Decision.DENY,
            reason=f"No role has permission: {permission}",
        )


# ============================================================================
# ABAC (Attribute-Based Access Control)
# ============================================================================


class ABACEngine:
    """
    Attribute-Based Access Control engine.

    Evaluates policies based on attributes (identity, resource, environment).
    """

    def __init__(self):
        self._policies: dict[str, Callable[[AuthzContext], AuthzResult]] = {}

    def register_policy(
        self,
        policy_id: str,
        policy_func: Callable[[AuthzContext], AuthzResult],
    ) -> None:
        """
        Register attribute-based policy.

        Args:
            policy_id: Policy identifier
            policy_func: Function that evaluates policy
        """
        self._policies[policy_id] = policy_func

    def evaluate(self, context: AuthzContext, policy_id: str) -> AuthzResult:
        """
        Evaluate specific policy.

        Args:
            context: Authorization context
            policy_id: Policy to evaluate

        Returns:
            Authorization result
        """
        if policy_id not in self._policies:
            return AuthzResult(
                decision=Decision.ABSTAIN,
                reason=f"Policy not found: {policy_id}",
            )

        return self._policies[policy_id](context)


# ============================================================================
# Scope-Based Authorization
# ============================================================================


class ScopeChecker:
    """
    OAuth2-style scope checking.

    Checks if identity has required scopes.
    """

    @staticmethod
    def check_scopes(
        available_scopes: list[str], required_scopes: list[str]
    ) -> bool:
        """
        Check if available scopes satisfy requirements.

        Args:
            available_scopes: Scopes available to identity
            required_scopes: Scopes required for action

        Returns:
            True if all required scopes are available
        """
        return set(required_scopes).issubset(set(available_scopes))

    @staticmethod
    def check(
        context: AuthzContext, required_scopes: list[str]
    ) -> AuthzResult:
        """
        Check scope-based authorization.

        Args:
            context: Authorization context
            required_scopes: Required scopes

        Returns:
            Authorization result
        """
        if ScopeChecker.check_scopes(context.scopes, required_scopes):
            return AuthzResult(
                decision=Decision.ALLOW,
                reason=f"Has required scopes: {required_scopes}",
            )

        return AuthzResult(
            decision=Decision.DENY,
            reason=f"Missing scopes: {set(required_scopes) - set(context.scopes)}",
        )


# ============================================================================
# Authorization Engine
# ============================================================================


class AuthzEngine:
    """
    Unified authorization engine.

    Combines RBAC, ABAC, and scope-based authorization.
    """

    def __init__(
        self,
        rbac: RBACEngine | None = None,
        abac: ABACEngine | None = None,
    ):
        self.rbac = rbac or RBACEngine()
        self.abac = abac or ABACEngine()
        self._policies: list[str] = []  # Ordered policy IDs

    def set_policy_order(self, policy_ids: list[str]) -> None:
        """Set evaluation order for policies."""
        self._policies = policy_ids

    def check_scope(
        self, context: AuthzContext, required_scopes: list[str]
    ) -> None:
        """
        Check scope requirements (raises if failed).

        Args:
            context: Authorization context
            required_scopes: Required scopes

        Raises:
            AUTHZ_INSUFFICIENT_SCOPE: Missing required scopes
        """
        result = ScopeChecker.check(context, required_scopes)
        if result.decision == Decision.DENY:
            raise AUTHZ_INSUFFICIENT_SCOPE(
                required_scopes=required_scopes,
                available_scopes=context.scopes,
            )

    def check_role(
        self, context: AuthzContext, required_roles: list[str]
    ) -> None:
        """
        Check role requirements (raises if failed).

        Args:
            context: Authorization context
            required_roles: Required roles

        Raises:
            AUTHZ_INSUFFICIENT_ROLE: Missing required roles
        """
        has_role = any(role in context.roles for role in required_roles)
        if not has_role:
            raise AUTHZ_INSUFFICIENT_ROLE(
                required_roles=required_roles,
                available_roles=context.roles,
            )

    def check_permission(
        self, context: AuthzContext, permission: str
    ) -> None:
        """
        Check RBAC permission (raises if failed).

        Args:
            context: Authorization context
            permission: Required permission

        Raises:
            AUTHZ_RESOURCE_FORBIDDEN: No permission for action
        """
        result = self.rbac.check(context, permission)
        if result.decision == Decision.DENY:
            raise AUTHZ_RESOURCE_FORBIDDEN(
                resource=context.resource,
                action=context.action,
                reason=result.reason,
            )

    def check_tenant(
        self, context: AuthzContext, resource_tenant_id: str
    ) -> None:
        """
        Check tenant isolation (multi-tenancy).

        Args:
            context: Authorization context
            resource_tenant_id: Tenant ID of resource

        Raises:
            AUTHZ_TENANT_MISMATCH: Tenant mismatch
        """
        if context.tenant_id != resource_tenant_id:
            raise AUTHZ_TENANT_MISMATCH(
                identity_tenant=context.tenant_id,
                resource_tenant=resource_tenant_id,
            )

    def check(self, context: AuthzContext) -> AuthzResult:
        """
        Comprehensive authorization check.

        Evaluates policies in order, returns first non-abstain decision.

        Args:
            context: Authorization context

        Returns:
            Authorization result
        """
        # Evaluate policies in order
        for policy_id in self._policies:
            result = self.abac.evaluate(context, policy_id)
            if result.decision != Decision.ABSTAIN:
                result.policy_id = policy_id
                return result

        # No policy made a decision - default deny
        return AuthzResult(
            decision=Decision.DENY,
            reason="No policy allowed access (default deny)",
        )

    def authorize(
        self,
        context: AuthzContext,
        raise_on_deny: bool = True,
    ) -> AuthzResult:
        """
        Authorize action (with optional exception raising).

        Args:
            context: Authorization context
            raise_on_deny: Raise exception on deny

        Returns:
            Authorization result

        Raises:
            AUTHZ_POLICY_DENIED: Authorization denied
        """
        result = self.check(context)

        if raise_on_deny and result.decision == Decision.DENY:
            raise AUTHZ_POLICY_DENIED(
                policy_id=result.policy_id or "default",
                denial_reason=result.reason or "Access denied",
                context={
                    "resource": context.resource,
                    "action": context.action,
                    "identity_id": context.identity.id,
                },
            )

        return result

    def list_permitted_actions(
        self,
        identity: Identity,
        resource: str,
        actions: list[str],
    ) -> list[str]:
        """
        List permitted actions for resource.

        Args:
            identity: Identity
            resource: Resource identifier
            actions: Actions to check

        Returns:
            List of permitted actions
        """
        permitted = []

        for action in actions:
            context = AuthzContext(
                identity=identity,
                resource=resource,
                action=action,
                scopes=identity.get_attribute("scopes", []),
                roles=identity.get_attribute("roles", []),
                tenant_id=identity.tenant_id,
            )

            result = self.check(context)
            if result.decision == Decision.ALLOW:
                permitted.append(action)

        return permitted


# ============================================================================
# Common Policy Builders
# ============================================================================


class PolicyBuilder:
    """Helper for building common authorization policies."""

    @staticmethod
    def owner_only(attribute: str = "owner_id") -> Callable[[AuthzContext], AuthzResult]:
        """
        Policy: Only resource owner can access.

        Args:
            attribute: Resource attribute containing owner ID

        Returns:
            Policy function
        """

        def policy(context: AuthzContext) -> AuthzResult:
            owner_id = context.attributes.get(attribute)
            if owner_id == context.identity.id:
                return AuthzResult(
                    decision=Decision.ALLOW,
                    reason="Identity is resource owner",
                )
            return AuthzResult(
                decision=Decision.DENY,
                reason="Identity is not resource owner",
            )

        return policy

    @staticmethod
    def admin_or_owner(
        admin_role: str = "admin", attribute: str = "owner_id"
    ) -> Callable[[AuthzContext], AuthzResult]:
        """
        Policy: Admin or resource owner can access.

        Args:
            admin_role: Role that grants admin access
            attribute: Resource attribute containing owner ID

        Returns:
            Policy function
        """

        def policy(context: AuthzContext) -> AuthzResult:
            # Check if admin
            if admin_role in context.roles:
                return AuthzResult(
                    decision=Decision.ALLOW,
                    reason=f"Identity has {admin_role} role",
                )

            # Check if owner
            owner_id = context.attributes.get(attribute)
            if owner_id == context.identity.id:
                return AuthzResult(
                    decision=Decision.ALLOW,
                    reason="Identity is resource owner",
                )

            return AuthzResult(
                decision=Decision.DENY,
                reason="Identity is neither admin nor owner",
            )

        return policy

    @staticmethod
    def time_based(
        allowed_hours: tuple[int, int] = (9, 17)
    ) -> Callable[[AuthzContext], AuthzResult]:
        """
        Policy: Allow access only during specific hours (UTC).

        Args:
            allowed_hours: Tuple of (start_hour, end_hour)

        Returns:
            Policy function
        """
        from datetime import datetime

        def policy(context: AuthzContext) -> AuthzResult:
            current_hour = datetime.utcnow().hour
            start, end = allowed_hours

            if start <= current_hour < end:
                return AuthzResult(
                    decision=Decision.ALLOW,
                    reason=f"Within allowed hours: {start}-{end}",
                )

            return AuthzResult(
                decision=Decision.DENY,
                reason=f"Outside allowed hours: {start}-{end} (current: {current_hour})",
            )

        return policy
