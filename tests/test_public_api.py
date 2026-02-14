"""
Tests for PR-Fix-C04: Phantom exports removed from __all__.

Validates that:
- Every name in aquilia.__all__ is actually importable.
- require_auth, require_scopes, require_roles are NOT in __all__.
"""
import pytest
import importlib


def test_all_exports_are_importable():
    """Every name in aquilia.__all__ must exist as an attribute."""
    import aquilia
    missing = []
    for name in aquilia.__all__:
        if not hasattr(aquilia, name):
            missing.append(name)
    assert not missing, f"Names in __all__ but not importable: {missing}"


def test_phantom_names_removed():
    """require_auth/require_scopes/require_roles must NOT be in __all__."""
    import aquilia
    phantoms = {"require_auth", "require_scopes", "require_roles"}
    present = phantoms & set(aquilia.__all__)
    assert not present, f"Phantom names still in __all__: {present}"


def test_import_star_succeeds():
    """'from aquilia import *' must not raise ImportError."""
    # We use importlib to simulate 'from aquilia import *'
    import aquilia
    ns = {}
    for name in aquilia.__all__:
        try:
            ns[name] = getattr(aquilia, name)
        except AttributeError as exc:
            pytest.fail(f"from aquilia import {name} failed: {exc}")
