"""
Tests for PR-Fix-C02: Hardcoded secret rejection.

Validates that:
- AuthConfig no longer defaults to an insecure secret.
- Integration.auth() does not inject an insecure fallback.
- Server startup rejects insecure secrets in non-DEV mode (NEEDS RUNTIME for full server test).
"""
import pytest


def test_auth_config_default_secret_is_none():
    """AuthConfig must NOT have a hardcoded insecure default secret."""
    from aquilia.config_builders import AuthConfig
    cfg = AuthConfig()
    assert cfg.secret_key is None, (
        f"AuthConfig.secret_key must default to None, got {cfg.secret_key!r}"
    )


def test_auth_config_explicit_secret():
    """Explicit secret_key must be preserved."""
    from aquilia.config_builders import AuthConfig
    cfg = AuthConfig(secret_key="my-strong-secret-key-here-256bit")
    assert cfg.secret_key == "my-strong-secret-key-here-256bit"


def test_integration_auth_no_secret_returns_none():
    """Integration.auth() without secret_key must produce None in tokens dict."""
    from aquilia.config_builders import Integration
    conf = Integration.auth()
    assert conf["tokens"]["secret_key"] is None


def test_integration_auth_with_explicit_secret():
    """Integration.auth() with explicit secret_key must keep it."""
    from aquilia.config_builders import Integration
    conf = Integration.auth(secret_key="explicit-key")
    assert conf["tokens"]["secret_key"] == "explicit-key"


def test_insecure_secret_not_present_in_defaults():
    """The string 'aquilia_insecure_dev_secret' must not appear in AuthConfig defaults."""
    from aquilia.config_builders import AuthConfig
    cfg = AuthConfig()
    d = cfg.to_dict()
    assert d["tokens"]["secret_key"] != "aquilia_insecure_dev_secret"
