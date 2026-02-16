"""
Aquilia CLI - ``aq test`` command.

Runs the project test suite using pytest with Aquilia-aware defaults:
- Sets ``AQUILIA_ENV=test``
- Auto-discovers tests in ``tests/`` and ``modules/*/tests/``
- Configures pytest-asyncio auto mode
- Supports coverage, verbosity, and pattern filtering
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional


def run_tests(
    *,
    paths: Optional[List[str]] = None,
    pattern: Optional[str] = None,
    verbose: bool = False,
    coverage: bool = False,
    coverage_html: bool = False,
    failfast: bool = False,
    markers: Optional[str] = None,
    parallel: bool = False,
    last_failed: bool = False,
    no_header: bool = False,
    extra_args: Optional[List[str]] = None,
) -> int:
    """
    Execute the test suite via pytest.

    Args:
        paths: Specific test file/dir paths (default: auto-discover).
        pattern: ``-k`` expression for test name filtering.
        verbose: Increase verbosity.
        coverage: Collect coverage data.
        coverage_html: Generate HTML coverage report.
        failfast: Stop on first failure.
        markers: pytest marker expression (``-m``).
        parallel: Run tests in parallel via ``pytest-xdist``.
        last_failed: Re-run only previously failed tests (``--lf``).
        no_header: Suppress pytest header output.
        extra_args: Additional raw pytest args.

    Returns:
        pytest exit code (0 = success).
    """
    # Ensure Aquilia env is set
    os.environ.setdefault("AQUILIA_ENV", "test")

    # Build pytest args
    args: list[str] = []

    # Auto-discover test directories
    if paths:
        args.extend(paths)
    else:
        discovered = _discover_test_dirs()
        args.extend(discovered)

    # Verbosity
    if verbose:
        args.append("-v")

    # Fail fast
    if failfast:
        args.append("-x")

    # Pattern filter
    if pattern:
        args.extend(["-k", pattern])

    # Marker filter
    if markers:
        args.extend(["-m", markers])

    # Parallel execution
    if parallel:
        args.extend(["-n", "auto"])

    # Last-failed only
    if last_failed:
        args.append("--lf")

    # No header
    if no_header:
        args.append("--no-header")

    # Coverage
    if coverage or coverage_html:
        args.extend(["--cov=aquilia", "--cov-report=term-missing"])
        if coverage_html:
            args.append("--cov-report=html")

    # Asyncio mode
    args.extend(["-o", "asyncio_mode=auto"])

    # Extra args
    if extra_args:
        args.extend(extra_args)

    try:
        import pytest as _pytest
        return _pytest.main(args)
    except ImportError:
        print(
            "pytest is not installed. "
            "Install it with: pip install pytest pytest-asyncio",
            file=sys.stderr,
        )
        return 1


def _discover_test_dirs() -> List[str]:
    """
    Auto-discover test directories in the workspace.

    Looks for:
    - ``tests/``
    - ``modules/*/tests/``
    - ``modules/*/test_*.py``
    """
    root = Path.cwd()
    dirs: list[str] = []

    # Top-level tests/ directory
    tests_dir = root / "tests"
    if tests_dir.is_dir():
        dirs.append(str(tests_dir))

    # Module-level tests
    modules_dir = root / "modules"
    if modules_dir.is_dir():
        for module_dir in modules_dir.iterdir():
            if not module_dir.is_dir():
                continue
            module_tests = module_dir / "tests"
            if module_tests.is_dir():
                dirs.append(str(module_tests))
            # Also grab standalone test files
            for test_file in module_dir.glob("test_*.py"):
                dirs.append(str(test_file))

    return dirs or ["tests"]
