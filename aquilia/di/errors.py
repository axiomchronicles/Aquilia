"""
DI-specific error types with rich diagnostics.
"""

from typing import List, Optional, Any


class DIError(Exception):
    """Base exception for DI errors."""
    pass


class ProviderNotFoundError(DIError):
    """Provider not found for requested token."""
    
    def __init__(
        self,
        token: str,
        tag: Optional[str] = None,
        candidates: Optional[List[str]] = None,
        requested_by: Optional[str] = None,
        location: Optional[tuple[str, int]] = None,
    ):
        self.token = token
        self.tag = tag
        self.candidates = candidates or []
        self.requested_by = requested_by
        self.location = location
        
        # Build helpful error message
        msg = f"No provider found for token={token}"
        if tag:
            msg += f" (tag={tag})"
        
        if requested_by:
            msg += f"\nRequested by: {requested_by}"
        
        if location:
            msg += f"\nLocation: {location[0]}:{location[1]}"
        
        if candidates:
            msg += f"\n\nCandidates found:"
            for candidate in candidates:
                msg += f"\n  - {candidate}"
            msg += f"\n\nSuggested fixes:"
            msg += f"\n  - Register a provider for {token}"
            if candidates:
                msg += f"\n  - Add Inject(tag='...') to disambiguate"
        
        super().__init__(msg)


class DependencyCycleError(DIError):
    """Circular dependency detected."""
    
    def __init__(
        self,
        cycle: List[str],
        locations: Optional[dict[str, tuple[str, int]]] = None,
    ):
        self.cycle = cycle
        self.locations = locations or {}
        
        # Build error message
        msg = "Detected dependency cycle:"
        for i, token in enumerate(cycle):
            arrow = " -> " if i < len(cycle) - 1 else ""
            msg += f"\n  {token}{arrow}"
        
        if locations:
            msg += "\n\nLocations:"
            for token, (file, line) in locations.items():
                if token in cycle:
                    msg += f"\n  - {file}:{line} ({token})"
        
        msg += "\n\nSuggested fixes:"
        msg += "\n  - Break cycle by using LazyProxy: manifest entry allow_lazy=True"
        msg += "\n  - Extract interface to decouple directionally"
        msg += "\n  - Restructure dependencies to remove cycle"
        
        super().__init__(msg)


class ScopeViolationError(DIError):
    """Scope violation detected (e.g., request-scoped injected into app-scoped)."""
    
    def __init__(
        self,
        provider_token: str,
        provider_scope: str,
        consumer_token: str,
        consumer_scope: str,
    ):
        self.provider_token = provider_token
        self.provider_scope = provider_scope
        self.consumer_token = consumer_token
        self.consumer_scope = consumer_scope
        
        msg = (
            f"Scope violation: {provider_scope}-scoped provider '{provider_token}' "
            f"injected into {consumer_scope}-scoped '{consumer_token}'. "
            f"\n\nScope rules forbid shorter-lived scopes from being injected into longer-lived scopes."
            f"\n\nSuggested fixes:"
            f"\n  - Change '{consumer_token}' to {provider_scope} scope"
            f"\n  - Change '{provider_token}' to {consumer_scope} scope"
            f"\n  - Use factory/provider pattern to defer instantiation"
        )
        
        super().__init__(msg)


class AmbiguousProviderError(DIError):
    """Multiple providers found for token without tag."""
    
    def __init__(
        self,
        token: str,
        providers: List[tuple[Optional[str], Any]],
    ):
        self.token = token
        self.providers = providers
        
        msg = f"Ambiguous provider for token={token}. Multiple providers found:"
        for tag, provider in providers:
            tag_str = f" (tag={tag})" if tag else " (no tag)"
            msg += f"\n  - {provider.meta.qualname}{tag_str}"
        
        msg += "\n\nSuggested fixes:"
        msg += "\n  - Add Inject(tag='...') to specify which provider to use"
        msg += "\n  - Remove duplicate provider registration"
        
        super().__init__(msg)


class ManifestValidationError(DIError):
    """Manifest validation failed."""
    
    def __init__(self, manifest_name: str, errors: List[str]):
        self.manifest_name = manifest_name
        self.errors = errors
        
        msg = f"Manifest validation failed for '{manifest_name}':"
        for error in errors:
            msg += f"\n  - {error}"
        
        super().__init__(msg)


class CrossAppDependencyError(DIError):
    """Cross-app dependency not declared in depends_on."""
    
    def __init__(
        self,
        consumer_app: str,
        provider_app: str,
        provider_token: str,
    ):
        self.consumer_app = consumer_app
        self.provider_app = provider_app
        self.provider_token = provider_token
        
        msg = (
            f"Cross-app dependency violation: App '{consumer_app}' "
            f"requires '{provider_token}' from app '{provider_app}', "
            f"but '{provider_app}' is not in depends_on.\n"
            f"\nSuggested fix:"
            f"\n  Add '{provider_app}' to depends_on list in {consumer_app} manifest"
        )
        
        super().__init__(msg)
