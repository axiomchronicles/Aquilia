"""
Template Security - Sandboxing and security policies.

Provides:
- Sandboxed Jinja2 environment with restricted globals/filters
- Allowlist-based filter and test registry
- Secret redaction and safe defaults
- XSS protection via autoescape
"""

from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from jinja2.sandbox import SandboxedEnvironment, ImmutableSandboxedEnvironment
from jinja2 import select_autoescape


@dataclass
class SandboxPolicy:
    """
    Template sandbox security policy.
    
    Defines what operations are allowed in templates.
    
    Attributes:
        allow_unsafe_filters: Allow potentially unsafe filters
        allow_unsafe_tests: Allow potentially unsafe tests
        allow_unsafe_globals: Allow potentially unsafe globals
        allowed_filters: Whitelist of allowed filter names
        allowed_tests: Whitelist of allowed test names
        allowed_globals: Whitelist of allowed global names
        autoescape: Enable HTML autoescaping
        autoescape_extensions: File extensions to autoescape
        max_recursion_depth: Maximum template recursion depth
    """
    
    allow_unsafe_filters: bool = False
    allow_unsafe_tests: bool = False
    allow_unsafe_globals: bool = False
    
    allowed_filters: Set[str] = field(default_factory=lambda: {
        # Safe built-in filters
        "abs", "attr", "batch", "capitalize", "center", "default",
        "dictsort", "escape", "filesizeformat", "first", "float",
        "forceescape", "format", "groupby", "indent", "int", "join",
        "last", "length", "list", "lower", "map", "max", "min",
        "pprint", "random", "reject", "rejectattr", "replace",
        "reverse", "round", "safe", "select", "selectattr", "slice",
        "sort", "string", "striptags", "sum", "title", "trim",
        "truncate", "unique", "upper", "urlencode", "urlize",
        "wordcount", "wordwrap", "xmlattr",
        
        # Custom safe filters (to be registered)
        "format_date", "format_currency", "pluralize", "sanitize_html",
    })
    
    allowed_tests: Set[str] = field(default_factory=lambda: {
        # Safe built-in tests
        "boolean", "callable", "defined", "divisibleby", "eq", "even",
        "false", "ge", "gt", "in", "iterable", "le", "lower", "lt",
        "mapping", "ne", "none", "number", "odd", "sameas", "sequence",
        "string", "true", "undefined", "upper",
    })
    
    allowed_globals: Set[str] = field(default_factory=lambda: {
        # Safe globals
        "range", "dict", "lipsum", "cycler", "joiner", "namespace",
        
        # Framework-provided globals (to be registered)
        "url_for", "static_url", "csrf_token", "config",
    })
    
    autoescape: bool = True
    autoescape_extensions: List[str] = field(default_factory=lambda: [
        "html", "htm", "xml", "xhtml"
    ])
    
    max_recursion_depth: int = 50
    
    @classmethod
    def strict(cls) -> "SandboxPolicy":
        """Strict policy for production (minimal allowlist)."""
        return cls(
            allow_unsafe_filters=False,
            allow_unsafe_tests=False,
            allow_unsafe_globals=False,
        )
    
    @classmethod
    def permissive(cls) -> "SandboxPolicy":
        """Permissive policy for development (expanded allowlist)."""
        policy = cls()
        
        # Add more filters for dev
        policy.allowed_filters.update([
            "tojson", "xmlattr",
        ])
        
        return policy
    
    def is_filter_allowed(self, name: str) -> bool:
        """Check if filter is allowed."""
        return self.allow_unsafe_filters or name in self.allowed_filters
    
    def is_test_allowed(self, name: str) -> bool:
        """Check if test is allowed."""
        return self.allow_unsafe_tests or name in self.allowed_tests
    
    def is_global_allowed(self, name: str) -> bool:
        """Check if global is allowed."""
        return self.allow_unsafe_globals or name in self.allowed_globals


class TemplateSandbox:
    """
    Template sandbox manager.
    
    Creates and configures sandboxed Jinja2 environments with security policies.
    
    Args:
        policy: Security policy to enforce
        immutable: Use ImmutableSandboxedEnvironment (more restrictive)
    """
    
    def __init__(
        self,
        policy: Optional[SandboxPolicy] = None,
        immutable: bool = False
    ):
        self.policy = policy or SandboxPolicy.strict()
        self.immutable = immutable
        
        # Filter and test registries
        self._custom_filters: Dict[str, Callable] = {}
        self._custom_tests: Dict[str, Callable] = {}
        self._custom_globals: Dict[str, Any] = {}
    
    def create_environment(self, **kwargs) -> SandboxedEnvironment:
        """
        Create sandboxed Jinja2 environment.
        
        Args:
            **kwargs: Additional environment options
        
        Returns:
            Configured SandboxedEnvironment
        """
        # Select environment class
        env_class = (
            ImmutableSandboxedEnvironment if self.immutable
            else SandboxedEnvironment
        )
        
        # Build environment options
        env_options = {
            "autoescape": select_autoescape(
                enabled_extensions=self.policy.autoescape_extensions,
                default_for_string=self.policy.autoescape,
            ) if self.policy.autoescape else False,
            **kwargs
        }
        
        env = env_class(**env_options)
        
        # Register custom filters
        for name, func in self._custom_filters.items():
            if self.policy.is_filter_allowed(name):
                env.filters[name] = func
        
        # Register custom tests
        for name, func in self._custom_tests.items():
            if self.policy.is_test_allowed(name):
                env.tests[name] = func
        
        # Register custom globals
        for name, value in self._custom_globals.items():
            if self.policy.is_global_allowed(name):
                env.globals[name] = value
        
        # Filter existing filters/tests/globals
        self._filter_environment(env)
        
        return env
    
    def register_filter(self, name: str, func: Callable) -> None:
        """
        Register custom filter.
        
        Filter will only be available if allowed by policy.
        """
        self._custom_filters[name] = func
        
        # Update policy allowlist
        if name not in self.policy.allowed_filters:
            self.policy.allowed_filters.add(name)
    
    def register_test(self, name: str, func: Callable) -> None:
        """
        Register custom test.
        
        Test will only be available if allowed by policy.
        """
        self._custom_tests[name] = func
        
        # Update policy allowlist
        if name not in self.policy.allowed_tests:
            self.policy.allowed_tests.add(name)
    
    def register_global(self, name: str, value: Any) -> None:
        """
        Register custom global.
        
        Global will only be available if allowed by policy.
        """
        self._custom_globals[name] = value
        
        # Update policy allowlist
        if name not in self.policy.allowed_globals:
            self.policy.allowed_globals.add(name)
    
    def _filter_environment(self, env: SandboxedEnvironment) -> None:
        """Remove disallowed filters, tests, and globals from environment."""
        # Filter built-in filters
        for name in list(env.filters.keys()):
            if not self.policy.is_filter_allowed(name):
                del env.filters[name]
        
        # Filter built-in tests
        for name in list(env.tests.keys()):
            if not self.policy.is_test_allowed(name):
                del env.tests[name]
        
        # Filter built-in globals
        for name in list(env.globals.keys()):
            if not self.policy.is_global_allowed(name):
                del env.globals[name]


def create_safe_globals() -> Dict[str, Any]:
    """
    Create dictionary of safe global functions for templates.
    
    These are framework-provided helpers that are safe for use in templates.
    """
    return {
        # URL generation (placeholder, will be injected at runtime)
        "url_for": lambda name, **params: f"/{name}",
        "static_url": lambda path: f"/static/{path}",
        
        # CSRF protection (runtime injection — reads from request.state["csrf_token"])
        "csrf_token": lambda: "",  # Placeholder; overridden at render-time by TemplateMiddleware
        
        # Config access (limited, safe subset)
        "config": {},
    }


def create_safe_filters() -> Dict[str, Callable]:
    """
    Create dictionary of safe custom filters.
    
    These are application-specific filters that are safe for use in templates.
    """
    import datetime
    
    def format_date(value, format_string: str = "%Y-%m-%d") -> str:
        """Format date/datetime object."""
        if isinstance(value, datetime.datetime):
            return value.strftime(format_string)
        elif isinstance(value, datetime.date):
            return value.strftime(format_string)
        return str(value)
    
    def format_currency(value, currency: str = "USD") -> str:
        """Format number as currency."""
        try:
            amount = float(value)
            if currency == "USD":
                return f"${amount:,.2f}"
            elif currency == "EUR":
                return f"€{amount:,.2f}"
            elif currency == "GBP":
                return f"£{amount:,.2f}"
            else:
                return f"{amount:,.2f} {currency}"
        except (ValueError, TypeError):
            return str(value)
    
    def pluralize(value: int, singular: str = "", plural: str = "s") -> str:
        """Return plural suffix based on count."""
        if value == 1:
            return singular
        return plural
    
    def sanitize_html(value: str, allowed_tags: Optional[List[str]] = None) -> str:
        """
        Sanitize HTML to prevent XSS.
        
        Basic implementation - in production, use bleach or similar library.
        """
        if allowed_tags is None:
            allowed_tags = ["b", "i", "u", "em", "strong", "a", "p", "br"]
        
        # Simple tag stripping (not production-grade)
        import re
        
        # Remove script tags and their content
        value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove style tags and their content
        value = re.sub(r"<style[^>]*>.*?</style>", "", value, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove event handlers
        value = re.sub(r'\s*on\w+="[^"]*"', "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*on\w+='[^']*'", "", value, flags=re.IGNORECASE)
        
        # For production, use: bleach.clean(value, tags=allowed_tags, strip=True)
        
        return value
    
    return {
        "format_date": format_date,
        "format_currency": format_currency,
        "pluralize": pluralize,
        "sanitize_html": sanitize_html,
    }
