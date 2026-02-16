"""
Trace CLI commands — ``aq trace status``, ``aq trace inspect``,
``aq trace journal``, ``aq trace clean``, ``aq trace diff``.

Registered into the main ``cli`` group by ``__main__.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click


# ═══════════════════════════════════════════════════════════════════════════
# aq trace — top-level group
# ═══════════════════════════════════════════════════════════════════════════


@click.group("trace")
def trace_group():
    """Inspect and manage the .aquilia/ trace directory."""
    pass


# ── status ───────────────────────────────────────────────────────────────


@trace_group.command("status")
@click.option("--dir", "-d", "workspace", default=".", help="Workspace root")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def trace_status(workspace: str, json_output: bool):
    """
    Show .aquilia/ trace directory status.

    Examples:
      aq trace status
      aq trace status --json
    """
    from aquilia.trace import AquiliaTrace

    trace = AquiliaTrace(Path(workspace))
    summary = trace.summary()

    if json_output:
        click.echo(json.dumps(summary, indent=2, default=str))
        return

    if not summary.get("exists"):
        click.secho("No .aquilia/ directory found.", fg="yellow")
        click.echo("Run the server to generate the trace.")
        return

    from ..utils.colors import section, kv, rule, _CHECK, _CROSS

    section(".aquilia/ Trace Status")
    kv("Root", str(summary['root']))
    kv("Locked", "Yes" if summary['locked'] else "No")
    kv("Files", ", ".join(summary['files']))

    manifest = summary.get("manifest", {})
    if manifest:
        kv("Mode", str(manifest.get('mode', '?')))
        kv("Apps", str(manifest.get('app_count', '?')))
        kv("Fingerprint", str(manifest.get('fingerprint', '?')[:16]))

    kv("Routes", str(summary.get('route_count', 0)))
    kv("Providers", str(summary.get('provider_count', 0)))
    kv("Models", str(summary.get('schema_count', 0)))
    kv("Events", str(summary.get('journal_events', 0)))

    # Last boot info
    last_boot_ts = summary.get("last_boot_ts")
    if last_boot_ts:
        boot_str = str(last_boot_ts)[:19]
        dur = summary.get("last_boot_duration_ms")
        dur_str = f" ({dur:.0f}ms)" if dur is not None else ""
        kv("Last boot", f"{boot_str}{dur_str}")

    # Last shutdown / uptime
    last_shutdown_ts = summary.get("last_shutdown_ts")
    if last_shutdown_ts:
        uptime = summary.get("last_uptime_s")
        uptime_str = f" (uptime {uptime:.1f}s)" if uptime is not None else ""
        kv("Last stop", f"{str(last_shutdown_ts)[:19]}{uptime_str}")

    # Health
    healthy = summary.get("healthy")
    if healthy is not None:
        health_sym = _CHECK if healthy else _CROSS
        health_label = "Healthy" if healthy else "Unhealthy"
        kv("Health", f"{health_sym} {health_label}")

    # Active subsystems
    active_subs = summary.get("active_subsystems", [])
    if active_subs:
        kv("Subsystems", ", ".join(active_subs))

    rule()


# ── inspect ──────────────────────────────────────────────────────────────


@trace_group.command("inspect")
@click.argument("section", type=click.Choice([
    "manifest", "routes", "di", "schema", "config", "diagnostics",
]))
@click.option("--dir", "-d", "workspace", default=".", help="Workspace root")
def trace_inspect(section: str, workspace: str):
    """
    Inspect a specific trace section.

    Examples:
      aq trace inspect manifest
      aq trace inspect routes
      aq trace inspect di
      aq trace inspect config
      aq trace inspect schema
      aq trace inspect diagnostics
    """
    from aquilia.trace import AquiliaTrace

    trace = AquiliaTrace(Path(workspace))
    if not trace.exists():
        click.secho("No .aquilia/ directory found.", fg="red")
        sys.exit(1)

    readers = {
        "manifest": trace.manifest.read,
        "routes": trace.routes.read,
        "di": trace.di_graph.read,
        "schema": trace.schema.read,
        "config": trace.config_snap.read,
        "diagnostics": trace.diagnostics.read,
    }

    data = readers[section]()
    if not data:
        click.secho(f"No {section} data found.", fg="yellow")
        return

    click.echo(json.dumps(data, indent=2, default=str))


# ── journal ──────────────────────────────────────────────────────────────


@trace_group.command("journal")
@click.option("--dir", "-d", "workspace", default=".", help="Workspace root")
@click.option("--tail", "-n", "count", default=20, help="Last N events")
@click.option("--event", "-e", default="", help="Filter by event type")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def trace_journal(workspace: str, count: int, event: str, json_output: bool):
    """
    View lifecycle journal events.

    Examples:
      aq trace journal
      aq trace journal --tail 5
      aq trace journal --event boot
      aq trace journal --event error --json
    """
    from aquilia.trace import AquiliaTrace

    trace = AquiliaTrace(Path(workspace))
    if not trace.exists():
        click.secho("No .aquilia/ directory found.", fg="red")
        sys.exit(1)

    events = trace.journal.tail(count)
    if event:
        events = [e for e in events if e.get("event") == event]

    if json_output:
        click.echo(json.dumps(events, indent=2, default=str))
        return

    if not events:
        click.secho("No journal events found.", fg="yellow")
        return

    click.secho(f"─── Journal (last {len(events)} events) ───", fg="cyan", bold=True)
    for ev in events:
        ts = ev.get("ts", "?")[:19]
        etype = ev.get("event", "?")
        color = {"boot": "green", "shutdown": "yellow", "error": "red", "warning": "magenta", "phase": "blue"}.get(etype, "white")
        summary = _event_summary(ev)
        click.secho(f"  [{ts}] ", fg="white", nl=False)
        click.secho(f"{etype:10}", fg=color, nl=False)
        click.echo(f"  {summary}")


def _event_summary(ev: dict) -> str:
    etype = ev.get("event", "")
    dur = ev.get("duration_ms")
    dur_str = f" [{dur:.0f}ms]" if dur is not None else ""
    if etype == "boot":
        return f"apps={ev.get('app_count', '?')} routes={ev.get('route_count', '?')} mode={ev.get('mode', '?')}{dur_str}"
    if etype == "shutdown":
        uptime = ev.get("uptime_s")
        uptime_str = f" uptime={uptime:.1f}s" if uptime is not None else ""
        return f"mode={ev.get('mode', '?')}{uptime_str}"
    if etype == "error":
        return ev.get("error", "")[:80]
    if etype == "warning":
        return ev.get("warning", "")[:80]
    if etype == "phase":
        s = ev.get("phase", "?")
        if ev.get("app"):
            s += f" app={ev['app']}"
        if ev.get("detail"):
            s += f" ({ev['detail']})"
        if ev.get("error"):
            s += f" error={ev['error'][:40]}"
        s += dur_str
        return s
    if etype == "custom":
        return ev.get("name", "?")
    return str(ev)[:80]


# ── clean ────────────────────────────────────────────────────────────────


@trace_group.command("clean")
@click.option("--dir", "-d", "workspace", default=".", help="Workspace root")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def trace_clean(workspace: str, force: bool):
    """
    Delete all trace files from .aquilia/.

    Examples:
      aq trace clean
      aq trace clean --force
    """
    from aquilia.trace import AquiliaTrace

    trace = AquiliaTrace(Path(workspace))
    if not trace.exists():
        click.secho("No .aquilia/ directory found.", fg="yellow")
        return

    if trace.is_locked() and not force:
        click.secho("Server is currently running (trace is locked).", fg="red")
        click.echo("Use --force to clean anyway.")
        sys.exit(1)

    if not force:
        click.confirm("Delete all trace files?", abort=True)

    count = trace.clean()
    from ..utils.colors import _CHECK
    click.secho(f"  {_CHECK} Cleaned {count} trace files.", fg="green")


# ── diff ─────────────────────────────────────────────────────────────────


@trace_group.command("diff")
@click.argument("other", type=click.Path(exists=True))
@click.option("--dir", "-d", "workspace", default=".", help="Workspace root")
@click.option("--section", "-s", type=click.Choice(["routes"]), default="routes", help="Section to diff")
def trace_diff(other: str, workspace: str, section: str):
    """
    Diff current trace against another trace directory.

    Examples:
      aq trace diff /path/to/old/.aquilia/routes.json
    """
    from aquilia.trace import AquiliaTrace

    trace = AquiliaTrace(Path(workspace))
    if not trace.exists():
        click.secho("No .aquilia/ directory found.", fg="red")
        sys.exit(1)

    if section == "routes":
        result = trace.routes.diff(Path(other))
    else:
        click.secho(f"Diff not supported for section: {section}", fg="red")
        sys.exit(1)

    added = result.get("added", [])
    removed = result.get("removed", [])
    changed = result.get("changed", [])

    if not added and not removed and not changed:
        click.secho("No differences found.", fg="green")
        return

    if added:
        click.secho(f"\n+ Added ({len(added)}):", fg="green", bold=True)
        for r in added:
            click.echo(f"  + {r.get('method', '?')} {r.get('path', '?')}")

    if removed:
        click.secho(f"\n- Removed ({len(removed)}):", fg="red", bold=True)
        for r in removed:
            click.echo(f"  - {r.get('method', '?')} {r.get('path', '?')}")

    if changed:
        click.secho(f"\n~ Changed ({len(changed)}):", fg="yellow", bold=True)
        for c in changed:
            cur = c["current"]
            prev = c["previous"]
            click.echo(f"  ~ {cur.get('method', '?')} {cur.get('path', '?')}")
            if cur.get("handler") != prev.get("handler"):
                click.echo(f"    handler: {prev.get('handler')} → {cur.get('handler')}")
