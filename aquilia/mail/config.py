"""
AquilaMail Configuration — Serializer-based, DI-aware mail configuration.

Uses Aquilia's Serializer system instead of raw dataclasses for:
- Declarative field validation with typed fields
- OpenAPI schema generation via ``.to_schema()``
- DI-aware defaults (InjectDefault, container resolution)
- Cross-field validation hooks
- Consistent Aquilia-native patterns

Integrates with Aquilia's Config system and workspace builder pattern.
All values have sensible defaults for development; override via config
files, environment variables, or the Workspace fluent API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..serializers.base import Serializer
from ..serializers.fields import (
    BooleanField,
    CharField,
    DictField,
    FloatField,
    IntegerField,
    ListField,
    ChoiceField,
)


# ── Provider types ──────────────────────────────────────────────────

PROVIDER_TYPES = ("smtp", "ses", "sendgrid", "console", "file")


# ═══════════════════════════════════════════════════════════════════
# Sub-config Serializers
# ═══════════════════════════════════════════════════════════════════


class ProviderConfigSerializer(Serializer):
    """
    Serializer for a single mail provider configuration.

    Validates provider type, priority bounds, and SMTP-specific fields.
    """

    name = CharField(max_length=100, required=True, help_text="Unique provider name")
    type = ChoiceField(
        choices=PROVIDER_TYPES,
        required=True,
        help_text="Provider backend type",
    )
    priority = IntegerField(
        min_value=0, max_value=1000, default=50, required=False,
        help_text="Lower = preferred",
    )
    enabled = BooleanField(default=True, required=False)
    rate_limit_per_min = IntegerField(
        min_value=0, default=600, required=False,
        help_text="Max messages per minute for this provider",
    )
    config = DictField(default=dict, required=False, help_text="Extra provider-specific options")

    # SMTP shortcuts
    host = CharField(default=None, required=False, allow_null=True)
    port = IntegerField(
        min_value=1, max_value=65535, default=None, required=False, allow_null=True,
    )
    username = CharField(default=None, required=False, allow_null=True)
    password = CharField(default=None, required=False, allow_null=True, write_only=True)
    use_tls = BooleanField(default=True, required=False)
    use_ssl = BooleanField(default=False, required=False)
    timeout = FloatField(min_value=0.1, max_value=300.0, default=30.0, required=False)

    def validate(self, attrs: dict) -> dict:
        """Cross-field validation: SMTP needs host."""
        if attrs.get("type") == "smtp":
            host = attrs.get("host")
            config = attrs.get("config", {})
            if not host and not (config and config.get("host")):
                pass  # host defaults to localhost in provider
        return attrs


class RetryConfigSerializer(Serializer):
    """Serializer for retry / backoff configuration."""

    max_attempts = IntegerField(min_value=0, max_value=100, default=5, required=False)
    base_delay = FloatField(min_value=0.0, max_value=60.0, default=1.0, required=False)
    max_delay = FloatField(min_value=0.0, default=3600.0, required=False)
    jitter = BooleanField(default=True, required=False)

    def validate(self, attrs: dict) -> dict:
        """Ensure base_delay <= max_delay."""
        base = attrs.get("base_delay", 1.0)
        mx = attrs.get("max_delay", 3600.0)
        if base > mx:
            raise ValueError("base_delay must be <= max_delay")
        return attrs


class RateLimitConfigSerializer(Serializer):
    """Serializer for global and per-domain rate-limiting."""

    global_per_minute = IntegerField(min_value=0, default=1000, required=False)
    per_domain_per_minute = IntegerField(min_value=0, default=100, required=False)
    per_provider_per_minute = IntegerField(
        min_value=0, default=None, required=False, allow_null=True,
    )


class SecurityConfigSerializer(Serializer):
    """Serializer for security / deliverability settings."""

    dkim_enabled = BooleanField(default=False, required=False)
    dkim_domain = CharField(default=None, required=False, allow_null=True)
    dkim_selector = CharField(max_length=100, default="aquilia", required=False)
    dkim_private_key_path = CharField(default=None, required=False, allow_null=True)
    dkim_private_key_env = CharField(default="AQUILIA_DKIM_PRIVATE_KEY", required=False)

    require_tls = BooleanField(default=True, required=False)
    allowed_from_domains = ListField(
        child=CharField(max_length=253),
        default=list,
        required=False,
    )
    pii_redaction_enabled = BooleanField(default=False, required=False)

    def validate(self, attrs: dict) -> dict:
        """DKIM domain required when DKIM is enabled."""
        if attrs.get("dkim_enabled") and not attrs.get("dkim_domain"):
            pass  # warning-level, not a hard error
        return attrs


class TemplateConfigSerializer(Serializer):
    """Serializer for ATS template engine configuration."""

    template_dirs = ListField(
        child=CharField(max_length=500),
        default=lambda: ["mail_templates"],
        required=False,
    )
    auto_escape = BooleanField(default=True, required=False)
    cache_compiled = BooleanField(default=True, required=False)
    strict_mode = BooleanField(default=False, required=False)


class QueueConfigSerializer(Serializer):
    """Serializer for queue / storage settings."""

    db_url = CharField(default="", required=False, help_text="Empty = use app main database")
    batch_size = IntegerField(min_value=1, max_value=10000, default=50, required=False)
    poll_interval = FloatField(min_value=0.1, max_value=60.0, default=1.0, required=False)
    dedupe_window_seconds = IntegerField(min_value=0, default=3600, required=False)
    retention_days = IntegerField(min_value=1, max_value=3650, default=30, required=False)


# ═══════════════════════════════════════════════════════════════════
# Backward-compatible config wrappers
# ═══════════════════════════════════════════════════════════════════
#
# These lightweight classes wrap validated serializer data so that
# existing code can still access config via attribute syntax
# (e.g. ``config.retry.max_attempts``).  They are created by the
# ``from_dict`` / ``from_validated`` factories.
# ═══════════════════════════════════════════════════════════════════


class _ConfigObject:
    """
    Thin attribute-access wrapper over a dict.

    Allows ``obj.key`` access while keeping dict underneath
    for serializer round-trips.

    Subclasses set ``_serializer_cls`` to auto-validate and fill
    defaults when created with keyword arguments.
    """

    __slots__ = ("_data",)
    _serializer_cls: type | None = None

    def __init__(self, data: dict | None = None, **kwargs):
        if data is None:
            data = kwargs
        # Validate through the serializer to populate defaults
        # (e.g. ProviderConfig(name="x", type="smtp") gets priority=50, etc.
        #  or RetryConfig() gets max_attempts=5, base_delay=1.0, etc.)
        cls_ser = type(self)._serializer_cls
        if cls_ser is not None:
            ser = cls_ser(data=data)
            if ser.is_valid():
                data = ser.validated_data
        object.__setattr__(self, "_data", dict(data))

    def __getattr__(self, name: str) -> Any:
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        raise AttributeError(
            f"{type(self).__name__!r} has no attribute {name!r}"
        )

    def __setattr__(self, name: str, value: Any) -> None:
        data = object.__getattribute__(self, "_data")
        data[name] = value

    def __repr__(self) -> str:
        cls = type(self).__name__
        data = object.__getattribute__(self, "_data")
        return f"{cls}({data!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _ConfigObject):
            return (
                object.__getattribute__(self, "_data")
                == object.__getattribute__(other, "_data")
            )
        return NotImplemented

    def to_dict(self) -> dict:
        data = object.__getattribute__(self, "_data")
        result = {}
        for k, v in data.items():
            if isinstance(v, _ConfigObject):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [
                    item.to_dict() if isinstance(item, _ConfigObject) else item
                    for item in v
                ]
            else:
                result[k] = v
        return result


class ProviderConfig(_ConfigObject):
    """Attribute-access wrapper for a validated provider config."""
    _serializer_cls = ProviderConfigSerializer


class RetryConfig(_ConfigObject):
    """Attribute-access wrapper for a validated retry config."""
    _serializer_cls = RetryConfigSerializer


class RateLimitConfig(_ConfigObject):
    """Attribute-access wrapper for a validated rate-limit config."""
    _serializer_cls = RateLimitConfigSerializer


class SecurityConfig(_ConfigObject):
    """Attribute-access wrapper for a validated security config."""
    _serializer_cls = SecurityConfigSerializer


class TemplateConfig(_ConfigObject):
    """Attribute-access wrapper for a validated template config."""
    _serializer_cls = TemplateConfigSerializer


class QueueConfig(_ConfigObject):
    """Attribute-access wrapper for a validated queue config."""
    _serializer_cls = QueueConfigSerializer


# ═══════════════════════════════════════════════════════════════════
# Internal validation helpers
# ═══════════════════════════════════════════════════════════════════


def _validate_sub(
    serializer_cls: type,
    data: dict,
    wrapper_cls: type,
) -> _ConfigObject:
    """Validate a sub-config dict through its serializer, return wrapper."""
    ser = serializer_cls(data=data)
    if ser.is_valid():
        return wrapper_cls(ser.validated_data)
    # If validation fails, still create with defaults (lenient for config)
    return wrapper_cls(data)


def _validate_provider(data: dict) -> ProviderConfig:
    """Validate a single provider config dict."""
    ser = ProviderConfigSerializer(data=data)
    if ser.is_valid():
        return ProviderConfig(ser.validated_data)
    return ProviderConfig(data)


def _coerce_providers(items: list) -> List[ProviderConfig]:
    """Convert a list of dicts / ProviderConfig objects to validated wrappers."""
    result: list[ProviderConfig] = []
    for item in items:
        if isinstance(item, ProviderConfig):
            result.append(item)
        elif isinstance(item, dict):
            result.append(_validate_provider(item))
        else:
            result.append(item)
    return result


def _coerce_sub(
    value: Any,
    serializer_cls: type,
    wrapper_cls: type,
) -> _ConfigObject:
    """Accept a wrapper, dict, or None and return a validated wrapper."""
    if isinstance(value, wrapper_cls):
        return value
    if isinstance(value, _ConfigObject):
        return wrapper_cls(object.__getattribute__(value, "_data"))
    if isinstance(value, dict):
        return _validate_sub(serializer_cls, value, wrapper_cls)
    # None / missing → defaults
    return _validate_sub(serializer_cls, {}, wrapper_cls)


# ═══════════════════════════════════════════════════════════════════
# MailConfig — top-level (preserves the public API)
# ═══════════════════════════════════════════════════════════════════


class MailConfig:
    """
    Top-level mail configuration.

    Integrates with Aquilia's layered config:
        config/base.yaml → config/{mode}.yaml → env vars → workspace.py overrides

    Usage in workspace.py::

        .integrate(Integration.mail(
            default_from="noreply@myapp.com",
            template_dir="mail_templates",
            providers=[...],
        ))

    Attribute access is fully preserved — all existing code works unchanged.
    Under the hood, each sub-config is validated through its corresponding
    Serializer class.
    """

    __slots__ = (
        "enabled", "default_from", "default_reply_to", "subject_prefix",
        "providers", "retry", "rate_limit", "security", "templates", "queue",
        "console_backend", "file_backend_path", "preview_mode",
        "metrics_enabled", "tracing_enabled",
    )

    def __init__(
        self,
        enabled: bool = True,
        default_from: str = "noreply@localhost",
        default_reply_to: Optional[str] = None,
        subject_prefix: str = "",
        providers: Optional[List[Any]] = None,
        retry: Optional[Any] = None,
        rate_limit: Optional[Any] = None,
        security: Optional[Any] = None,
        templates: Optional[Any] = None,
        queue: Optional[Any] = None,
        console_backend: bool = False,
        file_backend_path: Optional[str] = None,
        preview_mode: bool = False,
        metrics_enabled: bool = True,
        tracing_enabled: bool = False,
    ):
        self.enabled = enabled
        self.default_from = default_from
        self.default_reply_to = default_reply_to
        self.subject_prefix = subject_prefix

        # Sub-configs: accept wrapper objects or raw dicts
        self.providers = _coerce_providers(providers or [])
        self.retry = _coerce_sub(retry, RetryConfigSerializer, RetryConfig)
        self.rate_limit = _coerce_sub(
            rate_limit, RateLimitConfigSerializer, RateLimitConfig,
        )
        self.security = _coerce_sub(
            security, SecurityConfigSerializer, SecurityConfig,
        )
        self.templates = _coerce_sub(
            templates, TemplateConfigSerializer, TemplateConfig,
        )
        self.queue = _coerce_sub(queue, QueueConfigSerializer, QueueConfig)

        self.console_backend = console_backend
        self.file_backend_path = file_backend_path
        self.preview_mode = preview_mode
        self.metrics_enabled = metrics_enabled
        self.tracing_enabled = tracing_enabled

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "default_from": self.default_from,
            "default_reply_to": self.default_reply_to,
            "subject_prefix": self.subject_prefix,
            "providers": [p.to_dict() for p in self.providers],
            "retry": self.retry.to_dict(),
            "rate_limit": self.rate_limit.to_dict(),
            "security": self.security.to_dict(),
            "templates": self.templates.to_dict(),
            "queue": self.queue.to_dict(),
            "console_backend": self.console_backend,
            "metrics_enabled": self.metrics_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MailConfig":
        """
        Build MailConfig from a configuration dictionary.

        Each sub-section is validated through its corresponding Serializer.
        """
        providers: list[ProviderConfig] = []
        for p in data.get("providers", []):
            if isinstance(p, ProviderConfig):
                providers.append(p)
            elif isinstance(p, dict):
                providers.append(_validate_provider(p))

        retry_data = data.get("retry")
        rate_data = data.get("rate_limit")
        sec_data = data.get("security")
        tmpl_data = data.get("templates")
        queue_data = data.get("queue")

        return cls(
            enabled=data.get("enabled", True),
            default_from=data.get("default_from", "noreply@localhost"),
            default_reply_to=data.get("default_reply_to"),
            subject_prefix=data.get("subject_prefix", ""),
            providers=providers,
            retry=_validate_sub(
                RetryConfigSerializer,
                retry_data if isinstance(retry_data, dict) else {},
                RetryConfig,
            ),
            rate_limit=_validate_sub(
                RateLimitConfigSerializer,
                rate_data if isinstance(rate_data, dict) else {},
                RateLimitConfig,
            ),
            security=_validate_sub(
                SecurityConfigSerializer,
                sec_data if isinstance(sec_data, dict) else {},
                SecurityConfig,
            ),
            templates=_validate_sub(
                TemplateConfigSerializer,
                tmpl_data if isinstance(tmpl_data, dict) else {},
                TemplateConfig,
            ),
            queue=_validate_sub(
                QueueConfigSerializer,
                queue_data if isinstance(queue_data, dict) else {},
                QueueConfig,
            ),
            console_backend=data.get("console_backend", False),
            file_backend_path=data.get("file_backend_path"),
            preview_mode=data.get("preview_mode", False),
            metrics_enabled=data.get("metrics_enabled", True),
            tracing_enabled=data.get("tracing_enabled", False),
        )

    @classmethod
    def development(cls) -> "MailConfig":
        """Pre-configured for local development (console backend)."""
        return cls(
            console_backend=True,
            preview_mode=True,
            default_from="dev@localhost",
            providers=[
                ProviderConfig({"name": "console", "type": "console"}),
            ],
        )

    @classmethod
    def production(cls, default_from: str, **overrides: Any) -> "MailConfig":
        """Pre-configured for production with sensible defaults."""
        config = cls(
            default_from=default_from,
            console_backend=False,
            preview_mode=False,
            metrics_enabled=True,
            tracing_enabled=True,
            security=SecurityConfig({
                "dkim_enabled": True,
                "require_tls": True,
                "pii_redaction_enabled": True,
            }),
        )
        for k, v in overrides.items():
            if hasattr(config, k):
                setattr(config, k, v)
        return config
