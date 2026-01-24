"""
Aquilary registry error types with rich diagnostics.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ErrorSpan:
    """File location for error context."""
    
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    snippet: Optional[str] = None
    
    def __str__(self) -> str:
        parts = [self.file]
        if self.line is not None:
            parts.append(f":{self.line}")
            if self.column is not None:
                parts.append(f":{self.column}")
        return "".join(parts)


class RegistryError(Exception):
    """Base error for all Aquilary registry errors."""
    
    def __init__(
        self,
        message: str,
        *,
        span: Optional[ErrorSpan] = None,
        suggestion: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.span = span
        self.suggestion = suggestion
        self.details = details or {}
    
    def format_error(self) -> str:
        """Format error with rich diagnostics."""
        lines = []
        
        # Error header
        lines.append(f"❌ {self.__class__.__name__}: {self.message}")
        
        # Location
        if self.span:
            lines.append(f"   at {self.span}")
            if self.span.snippet:
                lines.append(f"\n   {self.span.snippet}")
        
        # Details
        if self.details:
            lines.append("\n   Details:")
            for key, value in self.details.items():
                lines.append(f"   - {key}: {value}")
        
        # Suggestion
        if self.suggestion:
            lines.append(f"\n   💡 Suggestion: {self.suggestion}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        return self.format_error()


class DependencyCycleError(RegistryError):
    """
    Circular dependency detected in app dependency graph.
    
    Example:
        app_a depends on app_b
        app_b depends on app_c
        app_c depends on app_a  <- CYCLE
    """
    
    def __init__(
        self,
        cycle: List[str],
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.cycle = cycle
        cycle_repr = " → ".join(cycle) + f" → {cycle[0]}"
        
        message = f"Circular dependency detected: {cycle_repr}"
        suggestion = (
            "Break the cycle by removing one dependency or introducing "
            "an intermediate abstraction. Consider using event-based "
            "communication instead of direct dependencies."
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={"cycle": cycle, "cycle_length": len(cycle)},
        )


class RouteConflictError(RegistryError):
    """
    Multiple controllers claim the same route path.
    
    Example:
        auth_app:   GET /users/:id
        admin_app:  GET /users/:id  <- CONFLICT
    """
    
    def __init__(
        self,
        path: str,
        method: str,
        providers: List[Dict[str, str]],
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.path = path
        self.method = method
        self.providers = providers
        
        provider_list = "\n".join(
            f"   - {p['app']}: {p['controller']}" for p in providers
        )
        
        message = (
            f"Route conflict: {method} {path}\n"
            f"   Claimed by:\n{provider_list}"
        )
        
        suggestion = (
            "Use unique route prefixes per app (e.g., /auth/users vs /admin/users), "
            "or use route priorities to explicitly resolve conflicts."
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={
                "path": path,
                "method": method,
                "provider_count": len(providers),
            },
        )


class ConfigValidationError(RegistryError):
    """
    Configuration validation failed.
    
    Aggregates multiple validation errors with file/line context.
    """
    
    def __init__(
        self,
        errors: List[Dict[str, Any]],
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.errors = errors
        
        error_count = len(errors)
        error_summary = "\n".join(
            f"   - {e['field']}: {e['message']}" for e in errors[:5]
        )
        if error_count > 5:
            error_summary += f"\n   ... and {error_count - 5} more errors"
        
        message = (
            f"Configuration validation failed ({error_count} error(s)):\n"
            f"{error_summary}"
        )
        
        suggestion = (
            "Check your config file against the schema. Run "
            "`aquilary validate --config` for detailed diagnostics."
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={"error_count": error_count, "errors": errors},
        )


class CrossAppUsageError(RegistryError):
    """
    App uses service/controller from another app without declaring dependency.
    
    Example:
        auth_app uses UserRepository from user_app
        but auth_app.depends_on = []  <- MISSING DEPENDENCY
    """
    
    def __init__(
        self,
        source_app: str,
        target_app: str,
        resource_type: str,
        resource_name: str,
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.source_app = source_app
        self.target_app = target_app
        self.resource_type = resource_type
        self.resource_name = resource_name
        
        message = (
            f"App '{source_app}' uses {resource_type} '{resource_name}' "
            f"from '{target_app}' without declaring dependency."
        )
        
        suggestion = (
            f"Add '{target_app}' to {source_app}.depends_on list in manifest:\n\n"
            f"   class {source_app.capitalize()}Manifest:\n"
            f"       depends_on = [..., \"{target_app}\"]"
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={
                "source_app": source_app,
                "target_app": target_app,
                "resource_type": resource_type,
                "resource_name": resource_name,
            },
        )


class ManifestValidationError(RegistryError):
    """
    Manifest structure is invalid.
    
    Missing required fields, wrong types, etc.
    """
    
    def __init__(
        self,
        manifest_name: str,
        validation_errors: List[str],
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.manifest_name = manifest_name
        self.validation_errors = validation_errors
        
        error_list = "\n".join(f"   - {e}" for e in validation_errors)
        
        message = (
            f"Manifest '{manifest_name}' validation failed:\n"
            f"{error_list}"
        )
        
        suggestion = (
            "Ensure manifest has required fields: name, version, controllers. "
            "Check manifest schema documentation for details."
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={
                "manifest": manifest_name,
                "error_count": len(validation_errors),
            },
        )


class DuplicateAppError(RegistryError):
    """
    Multiple manifests declare the same app name.
    
    Example:
        auth_app in auth/manifest.py
        auth_app in legacy/auth_manifest.py  <- DUPLICATE
    """
    
    def __init__(
        self,
        app_name: str,
        sources: List[str],
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.app_name = app_name
        self.sources = sources
        
        source_list = "\n".join(f"   - {s}" for s in sources)
        
        message = (
            f"Duplicate app name '{app_name}' declared in multiple manifests:\n"
            f"{source_list}"
        )
        
        suggestion = (
            "Each app must have a unique name. Rename one of the apps or "
            "remove the duplicate manifest."
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={"app_name": app_name, "source_count": len(sources)},
        )


class FrozenManifestMismatchError(RegistryError):
    """
    Current manifests don't match frozen fingerprint.
    
    Used in prod to prevent drift between deploys.
    """
    
    def __init__(
        self,
        expected_fingerprint: str,
        actual_fingerprint: str,
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.expected_fingerprint = expected_fingerprint
        self.actual_fingerprint = actual_fingerprint
        
        message = (
            f"Frozen manifest fingerprint mismatch!\n"
            f"   Expected: {expected_fingerprint}\n"
            f"   Actual:   {actual_fingerprint}"
        )
        
        suggestion = (
            "Run `aquilary freeze` to regenerate frozen manifest, or revert "
            "code changes to match the deployed fingerprint."
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={
                "expected": expected_fingerprint,
                "actual": actual_fingerprint,
            },
        )


class HotReloadError(RegistryError):
    """
    Hot-reload operation failed.
    
    File change caused registry rebuild failure.
    """
    
    def __init__(
        self,
        file_path: str,
        reason: str,
        *,
        span: Optional[ErrorSpan] = None,
    ):
        self.file_path = file_path
        self.reason = reason
        
        message = (
            f"Hot-reload failed for {file_path}:\n"
            f"   {reason}"
        )
        
        suggestion = (
            "Fix the error and save again. Hot-reload will automatically retry. "
            "If issue persists, restart the server."
        )
        
        super().__init__(
            message,
            span=span,
            suggestion=suggestion,
            details={"file": file_path, "reason": reason},
        )


@dataclass
class ValidationReport:
    """
    Aggregated validation report.
    
    Used during registry build to collect all errors before failing.
    """
    
    errors: List[RegistryError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: RegistryError) -> None:
        """Add error to report."""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add warning to report."""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if report has errors."""
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize report."""
        return {
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [
                {
                    "type": e.__class__.__name__,
                    "message": e.message,
                    "details": e.details,
                }
                for e in self.errors
            ],
            "warnings": self.warnings,
        }
    
    def to_exception(self) -> RegistryError:
        """Convert report to exception."""
        if not self.errors:
            raise ValueError("Cannot convert empty report to exception")
        
        if len(self.errors) == 1:
            return self.errors[0]
        
        # Multiple errors - return aggregated error
        error_summary = "\n".join(
            f"   {i+1}. {e.message}" for i, e in enumerate(self.errors)
        )
        
        return RegistryError(
            f"Multiple validation errors ({len(self.errors)}):\n{error_summary}",
            suggestion="Fix all errors and retry.",
            details=self.to_dict(),
        )
    
    def format_report(self) -> str:
        """Format report for display."""
        lines = []
        
        if self.errors:
            lines.append(f"❌ {len(self.errors)} error(s):")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"\n{i}. {error.format_error()}")
        
        if self.warnings:
            lines.append(f"\n⚠️  {len(self.warnings)} warning(s):")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"   {i}. {warning}")
        
        if not self.errors and not self.warnings:
            lines.append("✅ No errors or warnings")
        
        return "\n".join(lines)
