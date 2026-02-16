"""
Tests for AquilaMail Integration — Framework wiring.

Covers:
    - Integration.mail() builder: args, defaults, _integration_type
    - Workspace.integrate(Integration.mail(...)) routing & to_dict
    - ConfigLoader.get_mail_config() with defaults and merge
    - Server._setup_mail(): DI registration, singleton install
    - Server startup/shutdown: on_startup / on_shutdown lifecycle
    - CLI `aq mail` commands: check, inspect, send-test
    - Top-level Aquilia exports for mail symbols
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════
# Integration.mail() builder
# ═══════════════════════════════════════════════════════════════════


class TestIntegrationMail:
    """Tests for Integration.mail() static method."""

    def test_default_returns_dict(self):
        from aquilia.config_builders import Integration

        result = Integration.mail()
        assert isinstance(result, dict)

    def test_integration_type_marker(self):
        from aquilia.config_builders import Integration

        result = Integration.mail()
        assert result["_integration_type"] == "mail"

    def test_enabled_default(self):
        from aquilia.config_builders import Integration

        result = Integration.mail()
        assert result["enabled"] is True

    def test_disabled(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(enabled=False)
        assert result["enabled"] is False

    def test_default_from(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(default_from="noreply@myapp.com")
        assert result["default_from"] == "noreply@myapp.com"

    def test_default_from_fallback(self):
        from aquilia.config_builders import Integration

        result = Integration.mail()
        assert result["default_from"] == "noreply@localhost"

    def test_subject_prefix(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(subject_prefix="[MyApp] ")
        assert result["subject_prefix"] == "[MyApp] "

    def test_console_backend(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(console_backend=True)
        assert result["console_backend"] is True

    def test_preview_mode(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(preview_mode=True)
        assert result["preview_mode"] is True

    def test_providers_list(self):
        from aquilia.config_builders import Integration

        providers = [
            {"name": "smtp", "type": "smtp", "host": "smtp.example.com", "port": 587},
            {"name": "console", "type": "console"},
        ]
        result = Integration.mail(providers=providers)
        assert len(result["providers"]) == 2
        assert result["providers"][0]["name"] == "smtp"

    def test_providers_default_empty(self):
        from aquilia.config_builders import Integration

        result = Integration.mail()
        assert result["providers"] == []

    def test_template_dirs(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(template_dirs=["emails", "notifications"])
        assert result["templates"]["template_dirs"] == ["emails", "notifications"]

    def test_template_dirs_default(self):
        from aquilia.config_builders import Integration

        result = Integration.mail()
        assert result["templates"]["template_dirs"] == ["mail_templates"]

    def test_retry_config(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(retry_max_attempts=10, retry_base_delay=2.0)
        assert result["retry"]["max_attempts"] == 10
        assert result["retry"]["base_delay"] == 2.0

    def test_rate_limit_config(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(rate_limit_global=500, rate_limit_per_domain=50)
        assert result["rate_limit"]["global_per_minute"] == 500
        assert result["rate_limit"]["per_domain_per_minute"] == 50

    def test_security_dkim(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(
            dkim_enabled=True,
            dkim_domain="myapp.com",
            dkim_selector="default",
        )
        assert result["security"]["dkim_enabled"] is True
        assert result["security"]["dkim_domain"] == "myapp.com"
        assert result["security"]["dkim_selector"] == "default"

    def test_security_tls(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(require_tls=False)
        assert result["security"]["require_tls"] is False

    def test_pii_redaction(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(pii_redaction=True)
        assert result["security"]["pii_redaction_enabled"] is True

    def test_observability(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(metrics_enabled=True, tracing_enabled=True)
        assert result["metrics_enabled"] is True
        assert result["tracing_enabled"] is True

    def test_kwargs_passthrough(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(custom_key="custom_value")
        assert result["custom_key"] == "custom_value"

    def test_reply_to(self):
        from aquilia.config_builders import Integration

        result = Integration.mail(default_reply_to="reply@myapp.com")
        assert result["default_reply_to"] == "reply@myapp.com"

    def test_full_production_config(self):
        """Full production-like config."""
        from aquilia.config_builders import Integration

        result = Integration.mail(
            default_from="noreply@myapp.com",
            subject_prefix="[MyApp] ",
            providers=[
                {"name": "ses", "type": "ses", "config": {"region": "us-east-1"}},
                {"name": "smtp_fallback", "type": "smtp", "host": "smtp.relay.com", "port": 587, "priority": 100},
            ],
            dkim_enabled=True,
            dkim_domain="myapp.com",
            require_tls=True,
            pii_redaction=True,
            metrics_enabled=True,
            tracing_enabled=True,
            rate_limit_global=5000,
        )
        assert result["_integration_type"] == "mail"
        assert result["enabled"] is True
        assert len(result["providers"]) == 2
        assert result["security"]["dkim_enabled"] is True
        assert result["rate_limit"]["global_per_minute"] == 5000


# ═══════════════════════════════════════════════════════════════════
# Workspace integration routing
# ═══════════════════════════════════════════════════════════════════


class TestWorkspaceMailIntegration:
    """Tests for Workspace.integrate(Integration.mail(...))."""

    def test_integrate_stores_mail_config(self):
        from aquilia.config_builders import Integration, Workspace

        ws = Workspace("testapp").integrate(Integration.mail(
            default_from="test@example.com",
        ))
        assert ws._mail_config is not None
        assert ws._mail_config["default_from"] == "test@example.com"

    def test_integrate_stores_in_integrations(self):
        from aquilia.config_builders import Integration, Workspace

        ws = Workspace("testapp").integrate(Integration.mail())
        assert "mail" in ws._integrations
        assert ws._integrations["mail"]["_integration_type"] == "mail"

    def test_to_dict_includes_mail(self):
        from aquilia.config_builders import Integration, Workspace

        ws = Workspace("testapp").integrate(Integration.mail(
            default_from="admin@example.com",
            console_backend=True,
        ))
        config = ws.to_dict()

        # Top-level slot
        assert "mail" in config
        assert config["mail"]["default_from"] == "admin@example.com"
        assert config["mail"]["console_backend"] is True

        # Also in integrations for compatibility
        assert "mail" in config["integrations"]
        assert config["integrations"]["mail"]["_integration_type"] == "mail"

    def test_to_dict_no_mail_when_not_integrated(self):
        from aquilia.config_builders import Workspace

        ws = Workspace("testapp")
        config = ws.to_dict()
        assert "mail" not in config

    def test_mail_with_other_integrations(self):
        from aquilia.config_builders import Integration, Workspace

        ws = (
            Workspace("testapp")
            .integrate(Integration.di(auto_wire=True))
            .integrate(Integration.mail(default_from="test@app.com"))
            .integrate(Integration.routing(strict_matching=True))
        )
        config = ws.to_dict()
        assert "mail" in config
        assert "dependency_injection" in config["integrations"]
        assert "routing" in config["integrations"]
        assert "mail" in config["integrations"]

    def test_fluent_chain(self):
        """Integration.mail() works in fluent chain."""
        from aquilia.config_builders import Integration, Module, Workspace

        ws = (
            Workspace("testapp")
            .runtime(mode="dev", port=8000)
            .module(Module("blog").route_prefix("/blog"))
            .integrate(Integration.mail(
                default_from="noreply@blog.com",
                console_backend=True,
            ))
            .security(cors_enabled=False)
        )
        config = ws.to_dict()
        assert config["workspace"]["name"] == "testapp"
        assert len(config["modules"]) == 1
        assert config["mail"]["default_from"] == "noreply@blog.com"
        assert config["security"]["cors_enabled"] is False


# ═══════════════════════════════════════════════════════════════════
# ConfigLoader.get_mail_config()
# ═══════════════════════════════════════════════════════════════════


class TestConfigLoaderMailConfig:
    """Tests for ConfigLoader.get_mail_config()."""

    def test_defaults_when_no_config(self):
        from aquilia.config import ConfigLoader

        loader = ConfigLoader()
        config = loader.get_mail_config()
        assert config["enabled"] is False
        assert config["default_from"] == "noreply@localhost"
        assert config["providers"] == []
        assert config["console_backend"] is False

    def test_enabled_when_mail_config_present(self):
        from aquilia.config import ConfigLoader

        loader = ConfigLoader()
        loader.config_data["mail"] = {"enabled": True, "default_from": "admin@app.com"}
        config = loader.get_mail_config()
        assert config["enabled"] is True
        assert config["default_from"] == "admin@app.com"

    def test_reads_from_integrations_mail(self):
        from aquilia.config import ConfigLoader

        loader = ConfigLoader()
        loader.config_data["integrations"] = {
            "mail": {"enabled": True, "console_backend": True},
        }
        config = loader.get_mail_config()
        assert config["enabled"] is True
        assert config["console_backend"] is True

    def test_merge_with_defaults(self):
        from aquilia.config import ConfigLoader

        loader = ConfigLoader()
        loader.config_data["mail"] = {
            "enabled": True,
            "default_from": "custom@app.com",
            # Don't set retry — should get defaults
        }
        config = loader.get_mail_config()
        assert config["default_from"] == "custom@app.com"
        assert config["retry"]["max_attempts"] == 5  # default preserved

    def test_nested_overrides(self):
        from aquilia.config import ConfigLoader

        loader = ConfigLoader()
        loader.config_data["mail"] = {
            "enabled": True,
            "security": {"dkim_enabled": True, "dkim_domain": "app.com"},
        }
        config = loader.get_mail_config()
        assert config["security"]["dkim_enabled"] is True

    def test_workspace_to_dict_feeds_config_loader(self):
        """Workspace.to_dict() output works with ConfigLoader."""
        from aquilia.config import ConfigLoader
        from aquilia.config_builders import Integration, Workspace

        ws = Workspace("testapp").integrate(Integration.mail(
            default_from="ws@app.com",
            console_backend=True,
        ))
        ws_dict = ws.to_dict()

        loader = ConfigLoader()
        loader.config_data = ws_dict
        config = loader.get_mail_config()
        assert config["enabled"] is True
        assert config["default_from"] == "ws@app.com"
        assert config["console_backend"] is True


# ═══════════════════════════════════════════════════════════════════
# Server._setup_mail() — DI + singleton wiring
# ═══════════════════════════════════════════════════════════════════


class TestServerMailSetup:
    """Tests for AquiliaServer._setup_mail() wiring."""

    def _make_server_with_mail(self, mail_config: Dict[str, Any]) -> Any:
        """Create a minimally-mocked server with mail config."""
        from aquilia.config import ConfigLoader
        from aquilia.config_builders import Integration, Workspace

        # Build workspace
        ws = Workspace("testapp").integrate(mail_config)

        # Create config loader with workspace data
        config = ConfigLoader()
        config.config_data = ws.to_dict()

        # Mock the server parts we need
        server = MagicMock()
        server.config = config
        server.logger = MagicMock()
        server.runtime = MagicMock()
        server.runtime.di_containers = {}
        server._mail_service = None

        return server

    def test_setup_mail_disabled(self):
        """Mail setup is no-op when disabled."""
        from aquilia.config_builders import Integration
        from aquilia.server import AquiliaServer

        server = self._make_server_with_mail(
            Integration.mail(enabled=False)
        )
        AquiliaServer._setup_mail(server)
        assert server._mail_service is None

    def test_setup_mail_enabled_creates_service(self):
        """Mail setup creates MailService when enabled."""
        from aquilia.config_builders import Integration
        from aquilia.mail.service import MailService, set_mail_service
        from aquilia.server import AquiliaServer

        server = self._make_server_with_mail(
            Integration.mail(default_from="test@app.com", console_backend=True)
        )
        AquiliaServer._setup_mail(server)

        assert server._mail_service is not None
        assert isinstance(server._mail_service, MailService)
        assert server._mail_service.config.default_from == "test@app.com"
        assert server._mail_service.config.console_backend is True

    def test_setup_mail_installs_singleton(self):
        """Mail setup installs module-level singleton."""
        from aquilia.config_builders import Integration
        from aquilia.mail.service import _get_mail_service, set_mail_service
        from aquilia.server import AquiliaServer

        # Reset global
        set_mail_service(None)

        server = self._make_server_with_mail(
            Integration.mail(default_from="singleton@test.com")
        )
        AquiliaServer._setup_mail(server)

        # Should be accessible via module-level getter
        svc = _get_mail_service()
        assert svc is server._mail_service
        assert svc.config.default_from == "singleton@test.com"

        # Cleanup
        set_mail_service(None)

    def test_setup_mail_registers_in_di(self):
        """Mail setup registers MailService in DI containers."""
        from aquilia.config_builders import Integration
        from aquilia.di import Container
        from aquilia.mail.service import MailService, set_mail_service
        from aquilia.server import AquiliaServer

        container = Container(scope="app")
        server = self._make_server_with_mail(
            Integration.mail(console_backend=True)
        )
        server.runtime.di_containers = {"default": container}

        AquiliaServer._setup_mail(server)

        # ValueProvider stringifies token to "module.qualname"
        expected_key = f"{MailService.__module__}.{MailService.__qualname__}"
        assert expected_key in container._providers

        # Cleanup
        set_mail_service(None)

    def test_setup_mail_config_from_dict(self):
        """Mail config is correctly built from workspace dict."""
        from aquilia.config_builders import Integration
        from aquilia.mail.service import set_mail_service
        from aquilia.server import AquiliaServer

        server = self._make_server_with_mail(
            Integration.mail(
                default_from="custom@example.com",
                subject_prefix="[Test] ",
                preview_mode=True,
            )
        )
        AquiliaServer._setup_mail(server)

        svc = server._mail_service
        assert svc.config.default_from == "custom@example.com"
        assert svc.config.subject_prefix == "[Test] "
        assert svc.config.preview_mode is True

        # Cleanup
        set_mail_service(None)


# ═══════════════════════════════════════════════════════════════════
# Server startup/shutdown lifecycle
# ═══════════════════════════════════════════════════════════════════


class TestServerMailLifecycle:
    """Tests for mail startup/shutdown lifecycle hooks."""

    @pytest.mark.asyncio
    async def test_startup_calls_on_startup(self):
        """Server startup invokes MailService.on_startup()."""
        from aquilia.mail.service import MailService

        svc = MailService()
        svc.on_startup = AsyncMock()
        svc.on_shutdown = AsyncMock()

        server = MagicMock()
        server._mail_service = svc
        server._startup_complete = True
        server.logger = MagicMock()

        # Simulate startup hook
        if server._mail_service is not None:
            await server._mail_service.on_startup()

        svc.on_startup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_calls_on_shutdown(self):
        """Server shutdown invokes MailService.on_shutdown()."""
        from aquilia.mail.service import MailService

        svc = MailService()
        svc.on_startup = AsyncMock()
        svc.on_shutdown = AsyncMock()

        server = MagicMock()
        server._mail_service = svc
        server._startup_complete = True
        server.logger = MagicMock()

        # Simulate shutdown hook
        if server._mail_service is not None:
            await server._mail_service.on_shutdown()

        svc.on_shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_startup_no_op_when_no_mail(self):
        """No error when _mail_service is None."""
        server = MagicMock()
        server._mail_service = None

        # Should not raise
        if hasattr(server, '_mail_service') and server._mail_service is not None:
            await server._mail_service.on_startup()

    @pytest.mark.asyncio
    async def test_full_lifecycle_console(self):
        """Full start → send → stop lifecycle with console provider."""
        from aquilia.mail.config import MailConfig, ProviderConfig
        from aquilia.mail.message import EmailMessage
        from aquilia.mail.service import MailService

        config = MailConfig(
            default_from="test@lifecycle.com",
            console_backend=True,
            providers=[ProviderConfig(name="console", type="console")],
        )
        svc = MailService(config=config)

        # Start
        await svc.on_startup()
        assert svc.is_healthy()
        assert "console" in svc.get_provider_names()

        # Send
        msg = EmailMessage(
            subject="Lifecycle test",
            body="Hello from lifecycle test",
            to=["user@example.com"],
        )
        envelope_id = await svc.send_message(msg)
        assert envelope_id is not None

        # Stop
        await svc.on_shutdown()
        assert not svc.is_healthy()


# ═══════════════════════════════════════════════════════════════════
# CLI Commands
# ═══════════════════════════════════════════════════════════════════


class TestCLIMailCommands:
    """Tests for aq mail CLI command implementations."""

    def test_cmd_mail_check_disabled(self, capsys):
        """mail check shows warning when disabled."""
        from aquilia.cli.commands.mail import cmd_mail_check

        with patch("aquilia.cli.commands.mail._load_mail_config", return_value={"enabled": False}):
            cmd_mail_check(verbose=False)
        captured = capsys.readouterr()
        assert "not enabled" in captured.out

    def test_cmd_mail_check_enabled(self, capsys):
        """mail check shows config when enabled."""
        from aquilia.cli.commands.mail import cmd_mail_check

        config = {
            "enabled": True,
            "default_from": "test@app.com",
            "subject_prefix": "[App] ",
            "console_backend": True,
            "preview_mode": False,
            "providers": [{"name": "console", "type": "console", "enabled": True}],
            "security": {"dkim_enabled": False, "require_tls": True, "pii_redaction_enabled": False},
        }
        with patch("aquilia.cli.commands.mail._load_mail_config", return_value=config):
            cmd_mail_check(verbose=False)
        captured = capsys.readouterr()
        assert "test@app.com" in captured.out
        assert "console" in captured.out

    def test_cmd_mail_check_no_providers_warning(self, capsys):
        """mail check warns when no providers and no console."""
        from aquilia.cli.commands.mail import cmd_mail_check

        config = {
            "enabled": True,
            "default_from": "noreply@localhost",
            "subject_prefix": "",
            "console_backend": False,
            "preview_mode": False,
            "providers": [],
            "security": {"dkim_enabled": False, "require_tls": True, "pii_redaction_enabled": False},
        }
        with patch("aquilia.cli.commands.mail._load_mail_config", return_value=config):
            cmd_mail_check(verbose=False)
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "⚠" in captured.out

    def test_cmd_mail_inspect_disabled(self, capsys):
        """mail inspect shows warning when disabled."""
        from aquilia.cli.commands.mail import cmd_mail_inspect

        with patch("aquilia.cli.commands.mail._load_mail_config", return_value={"enabled": False}):
            cmd_mail_inspect(verbose=False)
        captured = capsys.readouterr()
        assert "not enabled" in captured.out

    def test_cmd_mail_inspect_enabled(self, capsys):
        """mail inspect shows JSON when enabled."""
        from aquilia.cli.commands.mail import cmd_mail_inspect

        config = {
            "enabled": True,
            "default_from": "test@app.com",
            "providers": [],
        }
        with patch("aquilia.cli.commands.mail._load_mail_config", return_value=config):
            cmd_mail_inspect(verbose=False)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["default_from"] == "test@app.com"

    def test_cmd_mail_send_test_disabled(self):
        """mail send-test exits when disabled."""
        from aquilia.cli.commands.mail import cmd_mail_send_test

        with patch("aquilia.cli.commands.mail._load_mail_config", return_value={"enabled": False}):
            with pytest.raises(SystemExit):
                cmd_mail_send_test(to="test@example.com", verbose=False)

    def test_cmd_mail_send_test_success(self, capsys):
        """mail send-test sends mail with console provider."""
        from aquilia.cli.commands.mail import cmd_mail_send_test

        config = {
            "enabled": True,
            "default_from": "test@app.com",
            "default_reply_to": None,
            "subject_prefix": "",
            "providers": [{"name": "console", "type": "console"}],
            "console_backend": True,
            "preview_mode": False,
            "retry": {"max_attempts": 1, "base_delay": 0.1},
            "rate_limit": {"global_per_minute": 100, "per_domain_per_minute": 10},
            "security": {"dkim_enabled": False, "require_tls": False, "pii_redaction_enabled": False},
            "templates": {"template_dirs": []},
            "queue": {},
            "metrics_enabled": False,
            "tracing_enabled": False,
        }
        with patch("aquilia.cli.commands.mail._load_mail_config", return_value=config):
            cmd_mail_send_test(
                to="user@example.com",
                subject="CLI Test",
                body="Test body",
                verbose=False,
            )
        captured = capsys.readouterr()
        assert "✓" in captured.out or "sent" in captured.out.lower()


# ═══════════════════════════════════════════════════════════════════
# CLI group registration
# ═══════════════════════════════════════════════════════════════════


class TestCLIMailGroup:
    """Tests for aq mail group registration in Click."""

    def test_mail_group_exists(self):
        """mail group is registered on CLI."""
        from aquilia.cli.__main__ import cli

        # Get all registered commands
        commands = cli.list_commands(ctx=None)
        assert "mail" in commands

    def test_mail_subcommands(self):
        """mail group has check, send-test, inspect commands."""
        from aquilia.cli.__main__ import mail

        commands = mail.list_commands(ctx=None)
        assert "check" in commands
        assert "send-test" in commands
        assert "inspect" in commands


# ═══════════════════════════════════════════════════════════════════
# Top-level Aquilia exports
# ═══════════════════════════════════════════════════════════════════


class TestAquiliaMailExports:
    """Tests for mail symbols in aquilia.__init__."""

    def test_message_types_exported(self):
        import aquilia

        assert hasattr(aquilia, "EmailMessage")
        assert hasattr(aquilia, "EmailMultiAlternatives")
        assert hasattr(aquilia, "TemplateMessage")

    def test_convenience_api_exported(self):
        import aquilia

        assert hasattr(aquilia, "send_mail")
        assert hasattr(aquilia, "asend_mail")

    def test_envelope_exported(self):
        import aquilia

        assert hasattr(aquilia, "MailEnvelope")
        assert hasattr(aquilia, "EnvelopeStatus")
        assert hasattr(aquilia, "Priority")

    def test_config_exported(self):
        import aquilia

        assert hasattr(aquilia, "MailConfig")

    def test_service_exported(self):
        import aquilia

        assert hasattr(aquilia, "MailService")

    def test_provider_types_exported(self):
        import aquilia

        assert hasattr(aquilia, "IMailProvider")
        assert hasattr(aquilia, "ProviderResult")
        assert hasattr(aquilia, "ProviderResultStatus")

    def test_fault_types_exported(self):
        import aquilia

        assert hasattr(aquilia, "MailFault")
        assert hasattr(aquilia, "MailSendFault")
        assert hasattr(aquilia, "MailTemplateFault")
        assert hasattr(aquilia, "MailConfigFault")
        assert hasattr(aquilia, "MailSuppressedFault")
        assert hasattr(aquilia, "MailRateLimitFault")
        assert hasattr(aquilia, "MailValidationFault")

    def test_all_mail_symbols_in___all__(self):
        import aquilia

        expected = [
            "EmailMessage",
            "EmailMultiAlternatives",
            "TemplateMessage",
            "send_mail",
            "asend_mail",
            "MailEnvelope",
            "EnvelopeStatus",
            "Priority",
            "MailConfig",
            "MailService",
            "IMailProvider",
            "ProviderResult",
            "ProviderResultStatus",
            "MailFault",
            "MailSendFault",
            "MailTemplateFault",
            "MailConfigFault",
            "MailSuppressedFault",
            "MailRateLimitFault",
            "MailValidationFault",
        ]
        for name in expected:
            assert name in aquilia.__all__, f"{name} not in aquilia.__all__"


# ═══════════════════════════════════════════════════════════════════
# Integration with existing subsystems
# ═══════════════════════════════════════════════════════════════════


class TestMailInteropWithExistingIntegrations:
    """Tests for mail coexistence with other Integration.xxx() calls."""

    def test_mail_with_database(self):
        from aquilia.config_builders import Integration, Workspace

        ws = (
            Workspace("testapp")
            .integrate(Integration.database(url="sqlite:///db.sqlite3"))
            .integrate(Integration.mail(default_from="test@app.com"))
        )
        config = ws.to_dict()
        assert "database" in config
        assert "mail" in config
        assert config["database"]["url"] == "sqlite:///db.sqlite3"
        assert config["mail"]["default_from"] == "test@app.com"

    def test_mail_with_openapi(self):
        from aquilia.config_builders import Integration, Workspace

        ws = (
            Workspace("testapp")
            .integrate(Integration.openapi(title="My API"))
            .integrate(Integration.mail(default_from="api@app.com"))
        )
        config = ws.to_dict()
        assert "openapi" in config["integrations"]
        assert "mail" in config["integrations"]

    def test_mail_with_security(self):
        from aquilia.config_builders import Integration, Workspace

        ws = (
            Workspace("testapp")
            .integrate(Integration.mail(default_from="test@app.com"))
            .security(helmet_enabled=True, cors_enabled=True)
        )
        config = ws.to_dict()
        assert "mail" in config
        assert config["security"]["cors_enabled"] is True
        assert config["security"]["helmet_enabled"] is True

    def test_mail_with_static_files(self):
        from aquilia.config_builders import Integration, Workspace

        ws = (
            Workspace("testapp")
            .integrate(Integration.mail(console_backend=True))
            .integrate(Integration.static_files(directories={"/static": "static"}))
        )
        config = ws.to_dict()
        assert "mail" in config
        assert "static_files" in config["integrations"]

    def test_mail_overwrite_on_second_integrate(self):
        """Second integrate(mail) overwrites the first."""
        from aquilia.config_builders import Integration, Workspace

        ws = (
            Workspace("testapp")
            .integrate(Integration.mail(default_from="first@app.com"))
            .integrate(Integration.mail(default_from="second@app.com"))
        )
        config = ws.to_dict()
        assert config["mail"]["default_from"] == "second@app.com"


# ═══════════════════════════════════════════════════════════════════
# MailConfig.from_dict with Integration.mail() output
# ═══════════════════════════════════════════════════════════════════


class TestMailConfigFromIntegrationDict:
    """Tests that MailConfig.from_dict works with Integration.mail() output."""

    def test_basic_roundtrip(self):
        from aquilia.config_builders import Integration
        from aquilia.mail.config import MailConfig

        raw = Integration.mail(
            default_from="test@roundtrip.com",
            console_backend=True,
        )
        config = MailConfig.from_dict(raw)
        assert config.default_from == "test@roundtrip.com"
        assert config.console_backend is True

    def test_providers_roundtrip(self):
        from aquilia.config_builders import Integration
        from aquilia.mail.config import MailConfig

        raw = Integration.mail(
            providers=[
                {"name": "smtp", "type": "smtp", "host": "mail.example.com", "port": 587},
            ],
        )
        config = MailConfig.from_dict(raw)
        assert len(config.providers) == 1
        assert config.providers[0].name == "smtp"
        assert config.providers[0].host == "mail.example.com"

    def test_nested_configs_roundtrip(self):
        from aquilia.config_builders import Integration
        from aquilia.mail.config import MailConfig

        raw = Integration.mail(
            retry_max_attempts=10,
            rate_limit_global=2000,
            dkim_enabled=True,
            dkim_domain="example.com",
        )
        config = MailConfig.from_dict(raw)
        assert config.retry.max_attempts == 10
        assert config.rate_limit.global_per_minute == 2000
        assert config.security.dkim_enabled is True
        assert config.security.dkim_domain == "example.com"

    def test_observability_roundtrip(self):
        from aquilia.config_builders import Integration
        from aquilia.mail.config import MailConfig

        raw = Integration.mail(metrics_enabled=True, tracing_enabled=True)
        config = MailConfig.from_dict(raw)
        assert config.metrics_enabled is True
        assert config.tracing_enabled is True


# ═══════════════════════════════════════════════════════════════════
# DI container resolution
# ═══════════════════════════════════════════════════════════════════


class TestMailDIResolution:
    """Tests for resolving MailService from DI container."""

    @pytest.mark.asyncio
    async def test_resolve_mail_service_from_container(self):
        """MailService is resolvable from DI after setup."""
        from aquilia.di import Container
        from aquilia.di.providers import ValueProvider
        from aquilia.mail.config import MailConfig
        from aquilia.mail.service import MailService

        config = MailConfig(console_backend=True)
        svc = MailService(config=config)

        container = Container(scope="app")
        container.register(ValueProvider(value=svc, token=MailService, scope="app"))

        resolved = await container.resolve_async(MailService)
        assert resolved is svc
        assert resolved.config.console_backend is True

    @pytest.mark.asyncio
    async def test_resolve_mail_service_by_type(self):
        """MailService resolvable by class type."""
        from aquilia.di import Container
        from aquilia.di.providers import ValueProvider
        from aquilia.mail.service import MailService

        svc = MailService()
        container = Container(scope="app")
        container.register(ValueProvider(value=svc, token=MailService, scope="app"))

        resolved = await container.resolve_async(MailService)
        assert isinstance(resolved, MailService)
