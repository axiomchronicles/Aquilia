"""
Aquilia Trace — The ``.aquilia/`` project tracking directory.

Inspired by how Next.js uses ``.next/`` but designed for Aquilia's
unique server-side architecture.  Tracks:

- **Build manifest** — registry fingerprint, module graph, route table
- **DI graph** — resolved providers, scopes, dependency tree
- **Route map** — compiled routes with specificity scores
- **Schema ledger** — model registry snapshots, migration history
- **Lifecycle journal** — startup/shutdown events with timing
- **Session vault** — active session statistics (not data)
- **Artifact index** — artifact store metadata cache
- **Config snapshot** — resolved config at boot (redacted secrets)
- **Diagnostics** — health probes, performance traces, error budget

The trace is written on every ``AquiliaServer.startup()`` and updated
on shutdown.  It is safe to delete — Aquilia regenerates it on next boot.

Usage::

    from aquilia.trace import AquiliaTrace

    trace = AquiliaTrace()                   # auto-detects workspace root
    trace.snapshot(server)                    # full snapshot from running server
    print(trace.manifest.fingerprint)         # last build fingerprint
    print(trace.routes.count)                 # number of compiled routes
"""

__all__ = [
    "AquiliaTrace",
    "TraceManifest",
    "TraceRouteMap",
    "TraceDIGraph",
    "TraceSchemaLedger",
    "TraceLifecycleJournal",
    "TraceConfigSnapshot",
    "TraceDiagnostics",
]

from .core import AquiliaTrace
from .manifests import TraceManifest
from .routes import TraceRouteMap
from .di_graph import TraceDIGraph
from .schema import TraceSchemaLedger
from .journal import TraceLifecycleJournal
from .config_snap import TraceConfigSnapshot
from .diagnostics import TraceDiagnostics
