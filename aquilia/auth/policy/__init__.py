"""
AquilAuth - Policy DSL Module

Authorization policy definitions and evaluation engine.
Provides a declarative policy language for RBAC/ABAC authorization.

This module integrates with:
- aquilia.auth.authz: Authorization engine (RBAC, ABAC)
- aquilia.auth.guards: Route-level guard decorators
- aquilia.di: Policy providers for dependency injection

Usage:
    from aquilia.auth.policy import Policy, Allow, Deny, rule

    class ArticlePolicy(Policy):
        resource = "article"

        @rule
        def can_read(self, identity, resource):
            return Allow()  # Anyone can read

        @rule
        def can_edit(self, identity, resource):
            if identity.id == resource.author_id:
                return Allow()
            if "editor" in identity.roles:
                return Allow()
            return Deny("Only author or editor can edit")
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PolicyDecision(Enum):
    """Result of a policy evaluation."""
    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"  # No opinion, defer to next policy


@dataclass
class PolicyResult:
    """Result of evaluating a policy rule."""
    decision: PolicyDecision
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def Allow(reason: Optional[str] = None, **metadata) -> PolicyResult:
    """Create an Allow decision."""
    return PolicyResult(decision=PolicyDecision.ALLOW, reason=reason, metadata=metadata)


def Deny(reason: Optional[str] = None, **metadata) -> PolicyResult:
    """Create a Deny decision."""
    return PolicyResult(decision=PolicyDecision.DENY, reason=reason, metadata=metadata)


def Abstain(reason: Optional[str] = None) -> PolicyResult:
    """Create an Abstain decision (defer to next rule/policy)."""
    return PolicyResult(decision=PolicyDecision.ABSTAIN, reason=reason)


def rule(func: Callable) -> Callable:
    """
    Decorator to mark a method as a policy rule.
    
    Rules are evaluated in definition order.
    First non-ABSTAIN result wins.
    """
    func.__is_policy_rule__ = True
    return func


class Policy:
    """
    Base class for resource-based authorization policies.
    
    Subclass and define rules using the @rule decorator.
    Integrates with AuthzEngine for enforcement.
    
    Example:
        class PostPolicy(Policy):
            resource = "post"
            
            @rule
            def can_create(self, identity, resource=None):
                if identity.has_role("author"):
                    return Allow()
                return Deny("Must be an author")
    """
    
    resource: str = ""
    
    def evaluate(self, action: str, identity: Any, resource: Any = None) -> PolicyResult:
        """
        Evaluate policy for a given action.
        
        Args:
            action: Action name (e.g., "read", "create", "edit", "delete")
            identity: Authenticated identity
            resource: Optional resource being accessed
            
        Returns:
            PolicyResult with decision
        """
        # Look for a rule named can_{action}
        rule_method = getattr(self, f"can_{action}", None)
        
        if rule_method and getattr(rule_method, "__is_policy_rule__", False):
            result = rule_method(identity, resource)
            if isinstance(result, PolicyResult):
                return result
        
        # Default: abstain (no opinion)
        return Abstain(f"No rule for action '{action}' on '{self.resource}'")
    
    def get_rules(self) -> List[str]:
        """Get list of defined rule names."""
        rules = []
        for name in dir(self):
            method = getattr(self, name, None)
            if callable(method) and getattr(method, "__is_policy_rule__", False):
                # Extract action from can_{action}
                if name.startswith("can_"):
                    rules.append(name[4:])
        return rules


class PolicyRegistry:
    """
    Registry for authorization policies.
    
    Integrates with DI to allow policies to be injected and
    resolved at runtime.
    """
    
    def __init__(self):
        self._policies: Dict[str, Policy] = {}
    
    def register(self, policy: Policy):
        """Register a policy by its resource name."""
        resource = policy.resource
        if not resource:
            resource = policy.__class__.__name__.replace("Policy", "").lower()
        self._policies[resource] = policy
    
    def get(self, resource: str) -> Optional[Policy]:
        """Get policy for a resource."""
        return self._policies.get(resource)
    
    def evaluate(self, resource: str, action: str, identity: Any, resource_obj: Any = None) -> PolicyResult:
        """
        Evaluate policy for a resource action.
        
        Args:
            resource: Resource type name
            action: Action being performed
            identity: Authenticated identity
            resource_obj: Optional resource instance
            
        Returns:
            PolicyResult - defaults to Deny if no policy found
        """
        policy = self._policies.get(resource)
        if policy is None:
            return Deny(f"No policy registered for resource '{resource}'")
        
        return policy.evaluate(action, identity, resource_obj)
    
    @property
    def resources(self) -> List[str]:
        """List all registered resource types."""
        return list(self._policies.keys())


__all__ = [
    "Policy",
    "PolicyResult",
    "PolicyDecision",
    "PolicyRegistry",
    "Allow",
    "Deny",
    "Abstain",
    "rule",
]
