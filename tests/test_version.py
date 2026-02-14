"""
Tests for PR-Fix-C05C06: Version and entrypoint synchronization.

Validates that:
- aquilia.__version__ matches pyproject.toml version.
- All version strings are consistent.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "Could not find version in pyproject.toml"
    return m.group(1)


def _read_setup_version() -> str:
    text = (ROOT / "setup.py").read_text()
    m = re.search(r'version\s*=\s*"([^"]+)"', text)
    assert m, "Could not find version in setup.py"
    return m.group(1)


def test_init_version_matches_pyproject():
    import aquilia
    expected = _read_pyproject_version()
    assert aquilia.__version__ == expected, (
        f"aquilia.__version__={aquilia.__version__!r} != pyproject.toml version={expected!r}"
    )


def test_setup_version_matches_pyproject():
    pyproject_v = _read_pyproject_version()
    setup_v = _read_setup_version()
    assert setup_v == pyproject_v, (
        f"setup.py version={setup_v!r} != pyproject.toml version={pyproject_v!r}"
    )


def test_pyproject_cli_entrypoint():
    """pyproject.toml must point aq to aquilia.cli.__main__:main."""
    text = (ROOT / "pyproject.toml").read_text()
    assert 'aq = "aquilia.cli.__main__:main"' in text, (
        "pyproject.toml CLI entrypoint does not point to aquilia.cli.__main__:main"
    )


def test_setup_cli_entrypoint():
    """setup.py must point aq to aquilia.cli.__main__:main."""
    text = (ROOT / "setup.py").read_text()
    assert "aq=aquilia.cli.__main__:main" in text, (
        "setup.py CLI entrypoint does not point to aquilia.cli.__main__:main"
    )
