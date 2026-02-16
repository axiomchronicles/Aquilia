"""
AquilaMail CLI commands — ``aq mail`` group.

Commands:
    send-test   Send a test email to verify provider configuration.
    inspect     Show current mail configuration and provider status.
    check       Validate mail configuration without starting the server.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click


def _load_mail_config() -> dict:
    """Load mail config from workspace.py or config files."""
    # Try workspace.py first
    workspace_path = Path("workspace.py")
    if workspace_path.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("workspace", str(workspace_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            if hasattr(mod, "workspace"):
                ws_dict = mod.workspace.to_dict()
                return ws_dict.get("mail", ws_dict.get("integrations", {}).get("mail", {}))

    # Fallback to ConfigLoader
    from aquilia.config import ConfigLoader

    config = ConfigLoader()
    return config.get_mail_config()


def cmd_mail_check(verbose: bool = False) -> None:
    """Validate mail configuration."""
    config = _load_mail_config()

    if not config or not config.get("enabled", False):
        click.echo(click.style("✗ Mail integration is not enabled.", fg="yellow"))
        click.echo("  Add .integrate(Integration.mail(...)) to your workspace.py")
        return

    click.echo(click.style("Mail Configuration Check", fg="cyan", bold=True))
    click.echo("─" * 40)

    # Basic settings
    click.echo(f"  Enabled:         {config.get('enabled')}")
    click.echo(f"  Default From:    {config.get('default_from', 'not set')}")
    click.echo(f"  Subject Prefix:  {config.get('subject_prefix', '(none)')!r}")
    click.echo(f"  Console Backend: {config.get('console_backend', False)}")
    click.echo(f"  Preview Mode:    {config.get('preview_mode', False)}")

    # Providers
    providers = config.get("providers", [])
    if providers:
        click.echo(f"\n  Providers ({len(providers)}):")
        for p in providers:
            name = p.get("name", "unnamed") if isinstance(p, dict) else getattr(p, "name", "unnamed")
            ptype = p.get("type", "?") if isinstance(p, dict) else getattr(p, "type", "?")
            enabled = p.get("enabled", True) if isinstance(p, dict) else getattr(p, "enabled", True)
            status = click.style("✓", fg="green") if enabled else click.style("✗", fg="red")
            click.echo(f"    {status} {name} ({ptype})")
    else:
        if config.get("console_backend"):
            click.echo(click.style("\n  ✓ Console backend will be auto-created", fg="green"))
        else:
            click.echo(click.style("\n  ⚠ No providers configured", fg="yellow"))

    # Security
    security = config.get("security", {})
    if isinstance(security, dict):
        click.echo(f"\n  Security:")
        click.echo(f"    DKIM:           {security.get('dkim_enabled', False)}")
        click.echo(f"    Require TLS:    {security.get('require_tls', True)}")
        click.echo(f"    PII Redaction:  {security.get('pii_redaction_enabled', False)}")

    issues = []
    if not config.get("default_from") or config["default_from"] == "noreply@localhost":
        issues.append("default_from is set to 'noreply@localhost' — update for production")
    if not providers and not config.get("console_backend"):
        issues.append("No providers and console_backend=False — mail won't be sent")

    if issues:
        click.echo(click.style(f"\n  Warnings ({len(issues)}):", fg="yellow"))
        for issue in issues:
            click.echo(f"    ⚠ {issue}")
    else:
        click.echo(click.style("\n  ✓ Configuration looks good!", fg="green"))


def cmd_mail_send_test(
    to: str,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """Send a test email."""
    config = _load_mail_config()

    if not config or not config.get("enabled", False):
        click.echo(click.style("✗ Mail integration is not enabled.", fg="red"))
        sys.exit(1)

    from aquilia.mail.config import MailConfig
    from aquilia.mail.service import MailService

    config_obj = MailConfig.from_dict(config)
    svc = MailService(config=config_obj)

    subject = subject or "Aquilia Mail Test"
    body = body or (
        "This is a test email sent from the Aquilia CLI.\n\n"
        f"If you received this, your mail configuration is working correctly.\n"
        f"Provider count: {len(config_obj.providers)}\n"
        f"Console backend: {config_obj.console_backend}\n"
    )

    async def _send():
        await svc.on_startup()
        try:
            from aquilia.mail.message import EmailMessage

            msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=config_obj.default_from,
                to=[to],
            )
            envelope_id = await svc.send_message(msg)
            click.echo(click.style(f"✓ Test email sent (envelope: {envelope_id})", fg="green"))
        finally:
            await svc.on_shutdown()

    try:
        asyncio.run(_send())
    except Exception as e:
        click.echo(click.style(f"✗ Send failed: {e}", fg="red"))
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def cmd_mail_inspect(verbose: bool = False) -> None:
    """Inspect mail configuration (JSON output)."""
    config = _load_mail_config()

    if not config or not config.get("enabled", False):
        click.echo(click.style("✗ Mail integration is not enabled.", fg="yellow"))
        return

    # Clean up non-serializable values
    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_clean(v) for v in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)

    cleaned = _clean(config)
    click.echo(json.dumps(cleaned, indent=2))
