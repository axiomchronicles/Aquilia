"""
Aquilate - Aquilia Native CLI System.

The `aq` command-line interface for manifest-driven, artifact-first
project orchestration.

Usage:
    aq init workspace <name>
    aq add module <name>
    aq validate
    aq compile
    aq run
    aq serve
    aq freeze
    aq inspect <target>
    aq migrate legacy

Philosophy:
- Manifest-first, not settings-first
- Composition over centralization
- Artifacts over runtime magic
- Explicit boundaries
- CLI as primary UX
- Static-first validation
"""

__version__ = "2.0.0"
__cli_name__ = "aq"


def main():
    """Wrapper to avoid eager import of __main__ which causes warnings with -m."""
    from .__main__ import main as _main
    return _main()
