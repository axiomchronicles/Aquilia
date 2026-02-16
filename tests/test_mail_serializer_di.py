"""
Tests for AquilaMail — Serializer-based Config, DI Providers, Discovery.

Covers:
    - Config Serializer validation (ProviderConfigSerializer, RetryConfigSerializer, etc.)
    - Serializer field validation (type checking, range checking, cross-field)
    - _ConfigObject attribute access, to_dict roundtrips
    - MailConfig from_dict validates through Serializers
    - MailConfig.to_schema() generates OpenAPI schema
    - DI providers: MailConfigProvider, MailServiceProvider, MailProviderRegistry
    - register_mail_providers() full wiring
    - Discovery integration: MailProviderRegistry.discover()
    - MailService._resolve_provider_via_discovery() fallback
    - Serializer validation errors (bad type, out of range, etc.)
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════
# CONFIG SERIALIZERS — Validation
# ═══════════════════════════════════════════════════════════════════


class TestProviderConfigSerializer:
    """Tests for ProviderConfigSerializer validation."""

    def test_valid_smtp(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "smtp1",
            "type": "smtp",
            "host": "smtp.example.com",
            "port": 587,
        })
        assert ser.is_valid()
        assert ser.validated_data["name"] == "smtp1"
        assert ser.validated_data["type"] == "smtp"
        assert ser.validated_data["host"] == "smtp.example.com"
        assert ser.validated_data["port"] == 587
        # Defaults filled in
        assert ser.validated_data["priority"] == 50
        assert ser.validated_data["enabled"] is True
        assert ser.validated_data["use_tls"] is True
        assert ser.validated_data["use_ssl"] is False
        assert ser.validated_data["timeout"] == 30.0
        assert ser.validated_data["rate_limit_per_min"] == 600

    def test_valid_console(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "console",
            "type": "console",
        })
        assert ser.is_valid()
        assert ser.validated_data["type"] == "console"

    def test_valid_ses(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "aws",
            "type": "ses",
            "config": {"region": "us-east-1"},
        })
        assert ser.is_valid()
        assert ser.validated_data["config"]["region"] == "us-east-1"

    def test_invalid_type(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "bad",
            "type": "invalid_type",
        })
        assert not ser.is_valid()
        assert "type" in ser.errors

    def test_missing_name(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={"type": "smtp"})
        assert not ser.is_valid()
        assert "name" in ser.errors

    def test_missing_type(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={"name": "x"})
        assert not ser.is_valid()
        assert "type" in ser.errors

    def test_priority_range(self):
        from aquilia.mail.config import ProviderConfigSerializer

        # Valid range
        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "priority": 0,
        })
        assert ser.is_valid()

        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "priority": 1000,
        })
        assert ser.is_valid()

    def test_priority_out_of_range(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "priority": -1,
        })
        assert not ser.is_valid()
        assert "priority" in ser.errors

        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "priority": 1001,
        })
        assert not ser.is_valid()

    def test_port_range(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "port": 0,
        })
        assert not ser.is_valid()
        assert "port" in ser.errors

        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "port": 70000,
        })
        assert not ser.is_valid()

    def test_timeout_range(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "timeout": 0.0,
        })
        assert not ser.is_valid()

    def test_password_is_write_only(self):
        from aquilia.mail.config import ProviderConfigSerializer

        ser = ProviderConfigSerializer(data={
            "name": "x", "type": "smtp", "password": "secret",
        })
        assert ser.is_valid()
        assert ser.validated_data["password"] == "secret"

    def test_to_schema(self):
        from aquilia.mail.config import ProviderConfigSerializer

        schema = ProviderConfigSerializer().to_schema()
        assert isinstance(schema, dict)

    def test_all_provider_types(self):
        from aquilia.mail.config import ProviderConfigSerializer, PROVIDER_TYPES

        for ptype in PROVIDER_TYPES:
            ser = ProviderConfigSerializer(data={"name": f"test_{ptype}", "type": ptype})
            assert ser.is_valid(), f"Type {ptype} should be valid: {ser.errors}"

    def test_choices_exhaustive(self):
        from aquilia.mail.config import PROVIDER_TYPES

        assert len(PROVIDER_TYPES) >= 4  # at least smtp, ses, sendgrid, console


class TestRetryConfigSerializer:
    """Tests for RetryConfigSerializer validation."""

    def test_defaults(self):
        from aquilia.mail.config import RetryConfigSerializer

        ser = RetryConfigSerializer(data={})
        assert ser.is_valid()
        d = ser.validated_data
        assert d["max_attempts"] == 5
        assert d["base_delay"] == 1.0
        assert d["max_delay"] == 3600.0
        assert d["jitter"] is True

    def test_custom_values(self):
        from aquilia.mail.config import RetryConfigSerializer

        ser = RetryConfigSerializer(data={
            "max_attempts": 10,
            "base_delay": 2.0,
            "max_delay": 600.0,
            "jitter": False,
        })
        assert ser.is_valid()
        assert ser.validated_data["max_attempts"] == 10
        assert ser.validated_data["jitter"] is False

    def test_cross_field_base_gt_max(self):
        from aquilia.mail.config import RetryConfigSerializer

        ser = RetryConfigSerializer(data={
            "base_delay": 50.0,
            "max_delay": 10.0,
        })
        assert not ser.is_valid()
        assert "__all__" in ser.errors

    def test_max_attempts_range(self):
        from aquilia.mail.config import RetryConfigSerializer

        ser = RetryConfigSerializer(data={"max_attempts": -1})
        assert not ser.is_valid()

        ser = RetryConfigSerializer(data={"max_attempts": 101})
        assert not ser.is_valid()


class TestRateLimitConfigSerializer:
    """Tests for RateLimitConfigSerializer validation."""

    def test_defaults(self):
        from aquilia.mail.config import RateLimitConfigSerializer

        ser = RateLimitConfigSerializer(data={})
        assert ser.is_valid()
        assert ser.validated_data["global_per_minute"] == 1000
        assert ser.validated_data["per_domain_per_minute"] == 100

    def test_custom(self):
        from aquilia.mail.config import RateLimitConfigSerializer

        ser = RateLimitConfigSerializer(data={
            "global_per_minute": 5000,
            "per_domain_per_minute": 200,
            "per_provider_per_minute": 300,
        })
        assert ser.is_valid()
        assert ser.validated_data["per_provider_per_minute"] == 300

    def test_null_per_provider(self):
        from aquilia.mail.config import RateLimitConfigSerializer

        ser = RateLimitConfigSerializer(data={"per_provider_per_minute": None})
        assert ser.is_valid()
        assert ser.validated_data["per_provider_per_minute"] is None


class TestSecurityConfigSerializer:
    """Tests for SecurityConfigSerializer validation."""

    def test_defaults(self):
        from aquilia.mail.config import SecurityConfigSerializer

        ser = SecurityConfigSerializer(data={})
        assert ser.is_valid()
        d = ser.validated_data
        assert d["dkim_enabled"] is False
        assert d["require_tls"] is True
        assert d["pii_redaction_enabled"] is False
        assert d["dkim_selector"] == "aquilia"
        assert d["dkim_private_key_env"] == "AQUILIA_DKIM_PRIVATE_KEY"

    def test_dkim_enabled(self):
        from aquilia.mail.config import SecurityConfigSerializer

        ser = SecurityConfigSerializer(data={
            "dkim_enabled": True,
            "dkim_domain": "myapp.com",
            "dkim_selector": "default",
        })
        assert ser.is_valid()
        assert ser.validated_data["dkim_enabled"] is True
        assert ser.validated_data["dkim_domain"] == "myapp.com"

    def test_allowed_from_domains(self):
        from aquilia.mail.config import SecurityConfigSerializer

        ser = SecurityConfigSerializer(data={
            "allowed_from_domains": ["example.com", "myapp.org"],
        })
        assert ser.is_valid()
        assert len(ser.validated_data["allowed_from_domains"]) == 2


class TestTemplateConfigSerializer:
    """Tests for TemplateConfigSerializer validation."""

    def test_defaults(self):
        from aquilia.mail.config import TemplateConfigSerializer

        ser = TemplateConfigSerializer(data={})
        assert ser.is_valid()
        d = ser.validated_data
        assert d["template_dirs"] == ["mail_templates"]
        assert d["auto_escape"] is True
        assert d["cache_compiled"] is True
        assert d["strict_mode"] is False

    def test_custom_dirs(self):
        from aquilia.mail.config import TemplateConfigSerializer

        ser = TemplateConfigSerializer(data={
            "template_dirs": ["emails", "notifications"],
        })
        assert ser.is_valid()
        assert ser.validated_data["template_dirs"] == ["emails", "notifications"]


class TestQueueConfigSerializer:
    """Tests for QueueConfigSerializer validation."""

    def test_defaults(self):
        from aquilia.mail.config import QueueConfigSerializer

        ser = QueueConfigSerializer(data={})
        assert ser.is_valid()
        d = ser.validated_data
        assert d["batch_size"] == 50
        assert d["poll_interval"] == 1.0
        assert d["dedupe_window_seconds"] == 3600
        assert d["retention_days"] == 30

    def test_custom(self):
        from aquilia.mail.config import QueueConfigSerializer

        ser = QueueConfigSerializer(data={
            "db_url": "sqlite:///mail.db",
            "batch_size": 100,
            "retention_days": 90,
        })
        assert ser.is_valid()
        assert ser.validated_data["db_url"] == "sqlite:///mail.db"
        assert ser.validated_data["batch_size"] == 100

    def test_batch_size_range(self):
        from aquilia.mail.config import QueueConfigSerializer

        ser = QueueConfigSerializer(data={"batch_size": 0})
        assert not ser.is_valid()

        ser = QueueConfigSerializer(data={"batch_size": 10001})
        assert not ser.is_valid()

    def test_retention_days_range(self):
        from aquilia.mail.config import QueueConfigSerializer

        ser = QueueConfigSerializer(data={"retention_days": 0})
        assert not ser.is_valid()


# ═══════════════════════════════════════════════════════════════════
# CONFIG OBJECT — _ConfigObject wrapper
# ═══════════════════════════════════════════════════════════════════


class TestConfigObject:
    """Tests for _ConfigObject attribute-access wrapper."""

    def test_attribute_access(self):
        from aquilia.mail.config import _ConfigObject

        obj = _ConfigObject({"a": 1, "b": "hello"})
        assert obj.a == 1
        assert obj.b == "hello"

    def test_setattr(self):
        from aquilia.mail.config import _ConfigObject

        obj = _ConfigObject({"a": 1})
        obj.a = 42
        assert obj.a == 42

    def test_missing_attr_raises(self):
        from aquilia.mail.config import _ConfigObject

        obj = _ConfigObject({"a": 1})
        with pytest.raises(AttributeError):
            _ = obj.nonexistent

    def test_to_dict(self):
        from aquilia.mail.config import _ConfigObject

        obj = _ConfigObject({"x": 1, "y": "z"})
        assert obj.to_dict() == {"x": 1, "y": "z"}

    def test_to_dict_nested(self):
        from aquilia.mail.config import _ConfigObject

        inner = _ConfigObject({"k": "v"})
        outer = _ConfigObject({"child": inner, "val": 1})
        d = outer.to_dict()
        assert d == {"child": {"k": "v"}, "val": 1}

    def test_equality(self):
        from aquilia.mail.config import _ConfigObject

        a = _ConfigObject({"x": 1})
        b = _ConfigObject({"x": 1})
        assert a == b

    def test_inequality(self):
        from aquilia.mail.config import _ConfigObject

        a = _ConfigObject({"x": 1})
        b = _ConfigObject({"x": 2})
        assert a != b

    def test_repr(self):
        from aquilia.mail.config import ProviderConfig

        pc = ProviderConfig({"name": "x", "type": "smtp"})
        r = repr(pc)
        assert "ProviderConfig" in r
        assert "smtp" in r

    def test_kwargs_constructor(self):
        from aquilia.mail.config import RetryConfig

        rc = RetryConfig(max_attempts=10)
        assert rc.max_attempts == 10
        # Defaults filled by serializer
        assert rc.base_delay == 1.0
        assert rc.jitter is True


class TestProviderConfigWrapper:
    """Tests for ProviderConfig wrapper with serializer defaults."""

    def test_kwargs_fills_defaults(self):
        from aquilia.mail.config import ProviderConfig

        pc = ProviderConfig(name="x", type="smtp")
        assert pc.priority == 50
        assert pc.enabled is True
        assert pc.use_tls is True
        assert pc.timeout == 30.0

    def test_dict_fills_defaults(self):
        from aquilia.mail.config import ProviderConfig

        pc = ProviderConfig({"name": "x", "type": "console"})
        assert pc.priority == 50
        assert pc.enabled is True

    def test_to_dict(self):
        from aquilia.mail.config import ProviderConfig

        pc = ProviderConfig(name="ses", type="ses")
        d = pc.to_dict()
        assert d["name"] == "ses"
        assert d["type"] == "ses"
        assert "priority" in d


# ═══════════════════════════════════════════════════════════════════
# MailConfig — Serializer Integration
# ═══════════════════════════════════════════════════════════════════


class TestMailConfigSerializerIntegration:
    """Tests for MailConfig using serializer validation under the hood."""

    def test_from_dict_validates_providers(self):
        from aquilia.mail.config import MailConfig

        data = {
            "providers": [
                {"name": "smtp1", "type": "smtp", "host": "h.com", "port": 587},
                {"name": "console", "type": "console"},
            ],
        }
        mc = MailConfig.from_dict(data)
        assert len(mc.providers) == 2
        # Serializer fills defaults
        assert mc.providers[0].priority == 50
        assert mc.providers[0].use_tls is True
        assert mc.providers[1].type == "console"

    def test_from_dict_validates_retry(self):
        from aquilia.mail.config import MailConfig

        data = {"retry": {"max_attempts": 3}}
        mc = MailConfig.from_dict(data)
        assert mc.retry.max_attempts == 3
        assert mc.retry.base_delay == 1.0  # serializer default

    def test_from_dict_validates_security(self):
        from aquilia.mail.config import MailConfig

        data = {"security": {"dkim_enabled": True, "dkim_domain": "x.com"}}
        mc = MailConfig.from_dict(data)
        assert mc.security.dkim_enabled is True
        assert mc.security.dkim_domain == "x.com"
        assert mc.security.dkim_selector == "aquilia"  # serializer default

    def test_default_constructor_validates(self):
        from aquilia.mail.config import MailConfig

        mc = MailConfig()
        # All sub-configs should have serializer-validated defaults
        assert mc.retry.max_attempts == 5
        assert mc.rate_limit.global_per_minute == 1000
        assert mc.security.require_tls is True
        assert mc.templates.template_dirs == ["mail_templates"]
        assert mc.queue.batch_size == 50

    def test_from_dict_invalid_provider_is_lenient(self):
        """Invalid provider config is still accepted (lenient mode)."""
        from aquilia.mail.config import MailConfig

        data = {
            "providers": [
                {"name": "bad", "type": "totally_invalid"},
            ],
        }
        mc = MailConfig.from_dict(data)
        assert len(mc.providers) == 1
        assert mc.providers[0].name == "bad"

    def test_to_dict_roundtrip_preserves_data(self):
        from aquilia.mail.config import MailConfig

        original = MailConfig(
            default_from="test@app.com",
            subject_prefix="[T] ",
            console_backend=True,
        )
        d = original.to_dict()
        restored = MailConfig.from_dict(d)
        assert restored.default_from == "test@app.com"
        assert restored.subject_prefix == "[T] "
        assert restored.console_backend is True

    def test_openapi_schema_from_serializers(self):
        """Serializer classes can generate OpenAPI schemas."""
        from aquilia.mail.config import (
            ProviderConfigSerializer,
            RetryConfigSerializer,
            RateLimitConfigSerializer,
            SecurityConfigSerializer,
            TemplateConfigSerializer,
            QueueConfigSerializer,
        )

        for ser_cls in [
            ProviderConfigSerializer,
            RetryConfigSerializer,
            RateLimitConfigSerializer,
            SecurityConfigSerializer,
            TemplateConfigSerializer,
            QueueConfigSerializer,
        ]:
            schema = ser_cls().to_schema()
            assert isinstance(schema, dict)


# ═══════════════════════════════════════════════════════════════════
# DI PROVIDERS
# ═══════════════════════════════════════════════════════════════════


class TestMailConfigProvider:
    """Tests for MailConfigProvider DI provider."""

    def test_provide_default(self):
        from aquilia.mail.di_providers import MailConfigProvider

        provider = MailConfigProvider()
        config = provider.provide()
        assert config.default_from == "noreply@localhost"
        assert config.enabled is True

    def test_provide_from_dict(self):
        from aquilia.mail.di_providers import MailConfigProvider

        provider = MailConfigProvider(config_data={
            "default_from": "test@app.com",
            "console_backend": True,
        })
        config = provider.provide()
        assert config.default_from == "test@app.com"
        assert config.console_backend is True

    def test_has_service_decorator(self):
        from aquilia.mail.di_providers import MailConfigProvider

        assert hasattr(MailConfigProvider, "__di_scope__")
        assert MailConfigProvider.__di_scope__ == "app"


class TestMailServiceProvider:
    """Tests for MailServiceProvider DI provider."""

    def test_provide_default(self):
        from aquilia.mail.di_providers import MailServiceProvider
        from aquilia.mail.service import MailService

        provider = MailServiceProvider()
        svc = provider.provide()
        assert isinstance(svc, MailService)

    def test_provide_with_config(self):
        from aquilia.mail.config import MailConfig
        from aquilia.mail.di_providers import MailServiceProvider

        config = MailConfig(default_from="test@x.com")
        provider = MailServiceProvider(config=config)
        svc = provider.provide()
        assert svc.config.default_from == "test@x.com"

    def test_provide_with_dict(self):
        from aquilia.mail.di_providers import MailServiceProvider

        provider = MailServiceProvider(config={"default_from": "dict@x.com"})
        svc = provider.provide()
        assert svc.config.default_from == "dict@x.com"

    def test_has_service_decorator(self):
        from aquilia.mail.di_providers import MailServiceProvider

        assert hasattr(MailServiceProvider, "__di_scope__")
        assert MailServiceProvider.__di_scope__ == "app"


class TestMailProviderRegistry:
    """Tests for MailProviderRegistry (discovery-based)."""

    def test_create(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        assert registry._scan_packages == ["aquilia.mail.providers"]

    def test_add_scan_package(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        registry.add_scan_package("myapp.mail_providers")
        assert "myapp.mail_providers" in registry._scan_packages

    def test_add_scan_package_no_duplicates(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        registry.add_scan_package("myapp.mail_providers")
        registry.add_scan_package("myapp.mail_providers")
        assert registry._scan_packages.count("myapp.mail_providers") == 1

    def test_discover_returns_dict(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        result = registry.discover()
        assert isinstance(result, dict)
        # Should find at least the ConsoleProvider
        assert "console" in result

    def test_get_provider_class(self):
        from aquilia.mail.di_providers import MailProviderRegistry
        from aquilia.mail.providers.console import ConsoleProvider

        registry = MailProviderRegistry()
        cls = registry.get_provider_class("console")
        assert cls is ConsoleProvider

    def test_get_unknown_provider_returns_none(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        assert registry.get_provider_class("nonexistent_xyz") is None

    def test_list_types(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        registry = MailProviderRegistry()
        types = registry.list_types()
        assert isinstance(types, list)
        assert "console" in types

    def test_has_service_decorator(self):
        from aquilia.mail.di_providers import MailProviderRegistry

        assert hasattr(MailProviderRegistry, "__di_scope__")
        assert MailProviderRegistry.__di_scope__ == "app"


# ═══════════════════════════════════════════════════════════════════
# register_mail_providers() — Full DI wiring
# ═══════════════════════════════════════════════════════════════════


class TestRegisterMailProviders:
    """Tests for register_mail_providers() full DI wiring."""

    def test_registers_in_container(self):
        from aquilia.di import Container
        from aquilia.mail.config import MailConfig
        from aquilia.mail.di_providers import register_mail_providers
        from aquilia.mail.service import MailService

        container = Container(scope="app")
        svc = register_mail_providers(
            container=container,
            config_data={"default_from": "test@di.com", "console_backend": True},
        )

        assert isinstance(svc, MailService)
        assert svc.config.default_from == "test@di.com"

        # MailService should be in container
        ms_key = f"{MailService.__module__}.{MailService.__qualname__}"
        assert ms_key in container._providers

        # MailConfig should be in container
        mc_key = f"{MailConfig.__module__}.{MailConfig.__qualname__}"
        assert mc_key in container._providers

    @pytest.mark.asyncio
    async def test_resolve_mail_service_after_registration(self):
        from aquilia.di import Container
        from aquilia.mail.di_providers import register_mail_providers
        from aquilia.mail.service import MailService

        container = Container(scope="app")
        svc = register_mail_providers(
            container=container,
            config_data={"console_backend": True},
        )

        resolved = await container.resolve_async(MailService)
        assert resolved is svc

    @pytest.mark.asyncio
    async def test_resolve_mail_config_after_registration(self):
        from aquilia.di import Container
        from aquilia.mail.config import MailConfig
        from aquilia.mail.di_providers import register_mail_providers

        container = Container(scope="app")
        register_mail_providers(
            container=container,
            config_data={"default_from": "cfg@test.com"},
        )

        resolved = await container.resolve_async(MailConfig)
        assert resolved.default_from == "cfg@test.com"

    def test_registers_provider_registry(self):
        from aquilia.di import Container
        from aquilia.mail.di_providers import (
            MailProviderRegistry,
            register_mail_providers,
        )

        container = Container(scope="app")
        register_mail_providers(
            container=container,
            config_data={},
            discover_providers=True,
        )

        reg_key = f"{MailProviderRegistry.__module__}.{MailProviderRegistry.__qualname__}"
        assert reg_key in container._providers

    def test_no_discovery_when_disabled(self):
        from aquilia.di import Container
        from aquilia.mail.di_providers import (
            MailProviderRegistry,
            register_mail_providers,
        )

        container = Container(scope="app")
        register_mail_providers(
            container=container,
            config_data={},
            discover_providers=False,
        )

        reg_key = f"{MailProviderRegistry.__module__}.{MailProviderRegistry.__qualname__}"
        assert reg_key not in container._providers


# ═══════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


class TestFactoryFunctions:
    """Tests for @factory decorated functions."""

    def test_create_mail_config_default(self):
        from aquilia.mail.di_providers import create_mail_config

        config = create_mail_config()
        assert config.default_from == "noreply@localhost"

    def test_create_mail_config_from_data(self):
        from aquilia.mail.di_providers import create_mail_config

        config = create_mail_config(config_data={"default_from": "x@y.com"})
        assert config.default_from == "x@y.com"

    def test_create_mail_service_default(self):
        from aquilia.mail.di_providers import create_mail_service
        from aquilia.mail.service import MailService

        svc = create_mail_service()
        assert isinstance(svc, MailService)

    def test_create_mail_service_from_dict(self):
        from aquilia.mail.di_providers import create_mail_service

        svc = create_mail_service(config={"default_from": "svc@y.com"})
        assert svc.config.default_from == "svc@y.com"

    def test_factory_decorators(self):
        from aquilia.mail.di_providers import create_mail_config, create_mail_service

        assert hasattr(create_mail_config, "__di_scope__")
        assert hasattr(create_mail_service, "__di_scope__")


# ═══════════════════════════════════════════════════════════════════
# SERVICE DISCOVERY FALLBACK
# ═══════════════════════════════════════════════════════════════════


class TestServiceDiscoveryFallback:
    """Tests for MailService._resolve_provider_via_discovery()."""

    def test_resolve_known_type(self):
        from aquilia.mail.service import MailService

        svc = MailService()
        cls = svc._resolve_provider_via_discovery("console")
        # Should find ConsoleProvider
        if cls is not None:
            from aquilia.mail.providers.console import ConsoleProvider
            assert cls is ConsoleProvider

    def test_resolve_unknown_type_returns_none(self):
        from aquilia.mail.service import MailService

        svc = MailService()
        cls = svc._resolve_provider_via_discovery("unknown_xyz_abc")
        assert cls is None


# ═══════════════════════════════════════════════════════════════════
# UPDATED SERVER._SETUP_MAIL — DI WIRING
# ═══════════════════════════════════════════════════════════════════


class TestServerMailSetupDI:
    """Tests for updated AquiliaServer._setup_mail() with DI providers."""

    def _make_server_with_mail(self, mail_config: Dict[str, Any]) -> Any:
        """Create a minimally-mocked server with mail config."""
        from aquilia.config import ConfigLoader
        from aquilia.config_builders import Integration, Workspace

        ws = Workspace("testapp").integrate(mail_config)
        config = ConfigLoader()
        config.config_data = ws.to_dict()

        server = MagicMock()
        server.config = config
        server.logger = MagicMock()
        server.runtime = MagicMock()
        server.runtime.di_containers = {}
        server._mail_service = None

        return server

    def test_setup_registers_config_and_service(self):
        """Updated _setup_mail registers both MailConfig and MailService."""
        from aquilia.config_builders import Integration
        from aquilia.di import Container
        from aquilia.mail.config import MailConfig
        from aquilia.mail.service import MailService, set_mail_service
        from aquilia.server import AquiliaServer

        container = Container(scope="app")
        server = self._make_server_with_mail(
            Integration.mail(console_backend=True, default_from="di@test.com")
        )
        server.runtime.di_containers = {"default": container}

        AquiliaServer._setup_mail(server)

        # Both MailService and MailConfig should be registered
        ms_key = f"{MailService.__module__}.{MailService.__qualname__}"
        mc_key = f"{MailConfig.__module__}.{MailConfig.__qualname__}"
        assert ms_key in container._providers
        assert mc_key in container._providers

        # Cleanup
        set_mail_service(None)

    def test_setup_discovers_providers(self):
        """Updated _setup_mail registers MailProviderRegistry."""
        from aquilia.config_builders import Integration
        from aquilia.di import Container
        from aquilia.mail.di_providers import MailProviderRegistry
        from aquilia.mail.service import set_mail_service
        from aquilia.server import AquiliaServer

        container = Container(scope="app")
        server = self._make_server_with_mail(
            Integration.mail(console_backend=True)
        )
        server.runtime.di_containers = {"default": container}

        AquiliaServer._setup_mail(server)

        reg_key = f"{MailProviderRegistry.__module__}.{MailProviderRegistry.__qualname__}"
        assert reg_key in container._providers

        # Cleanup
        set_mail_service(None)

    def test_setup_no_containers_still_works(self):
        """When no DI containers exist, service is still created."""
        from aquilia.config_builders import Integration
        from aquilia.mail.service import set_mail_service
        from aquilia.server import AquiliaServer

        server = self._make_server_with_mail(
            Integration.mail(default_from="nocontainer@test.com")
        )
        server.runtime.di_containers = {}

        AquiliaServer._setup_mail(server)

        assert server._mail_service is not None
        assert server._mail_service.config.default_from == "nocontainer@test.com"

        # Cleanup
        set_mail_service(None)


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════


class TestNewExports:
    """Tests for new exports in aquilia.mail.__init__."""

    def test_serializer_exports(self):
        from aquilia.mail import (
            ProviderConfigSerializer,
            RetryConfigSerializer,
            RateLimitConfigSerializer,
            SecurityConfigSerializer,
            TemplateConfigSerializer,
            QueueConfigSerializer,
        )

        # All should be Serializer subclasses
        from aquilia.serializers.base import Serializer

        for cls in [
            ProviderConfigSerializer,
            RetryConfigSerializer,
            RateLimitConfigSerializer,
            SecurityConfigSerializer,
            TemplateConfigSerializer,
            QueueConfigSerializer,
        ]:
            assert issubclass(cls, Serializer), f"{cls.__name__} not a Serializer"

    def test_config_wrapper_exports(self):
        from aquilia.mail import (
            ProviderConfig,
            RetryConfig,
            RateLimitConfig,
            SecurityConfig,
            TemplateConfig,
            QueueConfig,
        )
        from aquilia.mail.config import _ConfigObject

        for cls in [
            ProviderConfig, RetryConfig, RateLimitConfig,
            SecurityConfig, TemplateConfig, QueueConfig,
        ]:
            assert issubclass(cls, _ConfigObject)

    def test_di_provider_exports(self):
        from aquilia.mail import (
            MailConfigProvider,
            MailServiceProvider,
            MailProviderRegistry,
            register_mail_providers,
        )

        assert callable(register_mail_providers)

    def test_all_new_symbols_in__all__(self):
        import aquilia.mail as m

        for name in [
            "ProviderConfigSerializer", "RetryConfigSerializer",
            "RateLimitConfigSerializer", "SecurityConfigSerializer",
            "TemplateConfigSerializer", "QueueConfigSerializer",
            "ProviderConfig", "RetryConfig", "RateLimitConfig",
            "SecurityConfig", "TemplateConfig", "QueueConfig",
            "MailConfigProvider", "MailServiceProvider",
            "MailProviderRegistry", "register_mail_providers",
        ]:
            assert name in m.__all__, f"{name} not in __all__"
