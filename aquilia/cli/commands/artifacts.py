"""
Artifact CLI commands — ``aq artifact list``, ``aq artifact inspect``,
``aq artifact gc``, ``aq artifact export``, ``aq artifact verify``.

Registered into the main ``cli`` group by ``__main__.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click


# ═══════════════════════════════════════════════════════════════════════════
# aq artifact — top-level group
# ═══════════════════════════════════════════════════════════════════════════


@click.group("artifact")
def artifact_group():
    """Artifact management commands."""
    pass


# ── list ─────────────────────────────────────────────────────────────────


@artifact_group.command("list")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
@click.option("--kind", "-k", default="", help="Filter by artifact kind")
@click.option("--tag", "-t", default="", help="Filter by tag (key=value)")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def artifact_list(store_dir: str, kind: str, tag: str, json_output: bool):
    """
    List all artifacts in the store.

    Examples:
      aq artifact list
      aq artifact list --kind model
      aq artifact list --dir ./build/artifacts --tag env=production
    """
    from aquilia.artifacts import FilesystemArtifactStore

    store = FilesystemArtifactStore(store_dir)

    tag_key = ""
    tag_value = ""
    if tag and "=" in tag:
        tag_key, tag_value = tag.split("=", 1)

    artifacts = store.list_artifacts(kind=kind, tag_key=tag_key, tag_value=tag_value)

    if not artifacts:
        click.echo(click.style("No artifacts found.", fg="yellow"))
        return

    if json_output:
        data = [
            {
                "name": a.name,
                "version": a.version,
                "kind": a.kind,
                "digest": a.digest,
                "created_at": a.created_at,
                "tags": a.tags,
            }
            for a in artifacts
        ]
        click.echo(json.dumps(data, indent=2))
        return

    # Table output
    click.echo(click.style(f"{'NAME':<30} {'VERSION':<12} {'KIND':<12} {'DIGEST':<28} {'CREATED'}", fg="cyan"))
    click.echo("─" * 100)
    for a in artifacts:
        digest_short = a.digest[:24] + "…" if len(a.digest) > 24 else a.digest
        created = a.created_at[:19] if a.created_at else "—"
        click.echo(f"{a.name:<30} {a.version:<12} {a.kind:<12} {digest_short:<28} {created}")

    click.echo(click.style(f"\n{len(artifacts)} artifact(s)", fg="green"))


# ── inspect ──────────────────────────────────────────────────────────────


@artifact_group.command("inspect")
@click.argument("name")
@click.option("--version", "-V", default="", help="Artifact version")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def artifact_inspect(name: str, version: str, store_dir: str, json_output: bool):
    """
    Inspect an artifact by name.

    Examples:
      aq artifact inspect my-config
      aq artifact inspect my-model --version v1.0.0
      aq artifact inspect my-model -j
    """
    from aquilia.artifacts import FilesystemArtifactStore, ArtifactReader

    store = FilesystemArtifactStore(store_dir)
    reader = ArtifactReader(store)

    try:
        artifact = reader.load_or_fail(name, version=version)
    except FileNotFoundError:
        click.echo(click.style(f"✗ Artifact not found: {name}", fg="red"))
        sys.exit(1)

    info = reader.inspect(artifact)

    if json_output:
        click.echo(json.dumps(info, indent=2, default=str))
        return

    click.echo(click.style(f"Artifact: {info['name']}:{info['version']}", fg="cyan", bold=True))
    click.echo(f"  Kind:       {info['kind']}")
    click.echo(f"  Digest:     {info['digest']}")
    click.echo(f"  Created:    {info.get('created_at', '—')}")
    click.echo(f"  Created by: {info.get('created_by', '—')}")
    click.echo(f"  Git SHA:    {info.get('git_sha', '—')}")
    click.echo(f"  Hostname:   {info.get('hostname', '—')}")

    if info.get("tags"):
        click.echo("  Tags:")
        for k, v in info["tags"].items():
            click.echo(f"    {k}: {v}")

    if info.get("metadata_keys"):
        click.echo("  Metadata keys:")
        for k in info["metadata_keys"]:
            click.echo(f"    {k}")

    payload_preview = info.get("payload_preview", "")
    if payload_preview:
        click.echo(f"  Payload:    {payload_preview}")


# ── verify ───────────────────────────────────────────────────────────────


@artifact_group.command("verify")
@click.argument("name")
@click.option("--version", "-V", default="", help="Artifact version")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
def artifact_verify(name: str, version: str, store_dir: str):
    """
    Verify the integrity of an artifact.

    Examples:
      aq artifact verify my-config
      aq artifact verify my-model --version v1.0.0
    """
    from aquilia.artifacts import FilesystemArtifactStore, ArtifactReader

    store = FilesystemArtifactStore(store_dir)
    reader = ArtifactReader(store)

    result = reader.verify_by_name(name, version=version)

    if result is None:
        click.echo(click.style(f"✗ Artifact not found: {name}", fg="red"))
        sys.exit(1)
    elif result:
        click.echo(click.style(f"✓ Integrity OK: {name}", fg="green"))
    else:
        click.echo(click.style(f"✗ Integrity FAILED: {name}", fg="red"))
        sys.exit(1)


# ── verify-all ───────────────────────────────────────────────────────────


@artifact_group.command("verify-all")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def artifact_verify_all(store_dir: str, json_output: bool):
    """
    Verify integrity of ALL artifacts in the store.

    Examples:
      aq artifact verify-all
      aq artifact verify-all -j
    """
    from aquilia.artifacts import FilesystemArtifactStore, ArtifactReader

    store = FilesystemArtifactStore(store_dir)
    reader = ArtifactReader(store)

    passed, failed, failed_names = reader.batch_verify()

    if json_output:
        click.echo(json.dumps({"passed": passed, "failed": failed, "failed_names": failed_names}))
        return

    click.echo(click.style(f"Verified: {passed} passed, {failed} failed", fg="green" if failed == 0 else "red"))
    for name in failed_names:
        click.echo(click.style(f"  ✗ {name}", fg="red"))

    if failed:
        sys.exit(1)


# ── gc ───────────────────────────────────────────────────────────────────


@artifact_group.command("gc")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
@click.option("--keep", "-k", multiple=True, help="Digests to keep (repeatable)")
@click.option("--dry-run", is_flag=True, help="Show what would be removed")
def artifact_gc(store_dir: str, keep: tuple, dry_run: bool):
    """
    Garbage-collect unreferenced artifacts.

    Examples:
      aq artifact gc
      aq artifact gc --keep sha256:abc123 --keep sha256:def456
      aq artifact gc --dry-run
    """
    from aquilia.artifacts import FilesystemArtifactStore

    store = FilesystemArtifactStore(store_dir)
    referenced = set(keep)

    if dry_run:
        # Show what would be removed
        artifacts = store.list_artifacts()
        unreferenced = [a for a in artifacts if a.digest not in referenced]
        if not unreferenced:
            click.echo(click.style("Nothing to collect.", fg="green"))
            return
        click.echo(click.style("Would remove:", fg="yellow"))
        for a in unreferenced:
            click.echo(f"  {a.qualified_name}  {a.digest[:24]}…")
        click.echo(click.style(f"\n{len(unreferenced)} artifact(s) would be removed", fg="yellow"))
        return

    removed = store.gc(referenced)
    if removed:
        click.echo(click.style(f"✓ Collected {removed} artifact(s)", fg="green"))
    else:
        click.echo(click.style("Nothing to collect.", fg="green"))


# ── export ───────────────────────────────────────────────────────────────


@artifact_group.command("export")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
@click.option("--output", "-o", default="bundle.aq.json", help="Output bundle file")
@click.option("--name", "-n", multiple=True, help="Artifact names to export (repeatable)")
def artifact_export(store_dir: str, output: str, name: tuple):
    """
    Export artifacts as a bundle.

    Examples:
      aq artifact export --name my-config --name my-model -o release.aq.json
      aq artifact export   # exports all
    """
    from aquilia.artifacts import FilesystemArtifactStore

    store = FilesystemArtifactStore(store_dir)

    if name:
        names = list(name)
    else:
        # Export all
        names = list({a.name for a in store.list_artifacts()})

    if not names:
        click.echo(click.style("No artifacts to export.", fg="yellow"))
        return

    try:
        bundle_path = store.export_bundle(names, output)
        click.echo(click.style(f"✓ Bundle exported: {bundle_path} ({len(names)} artifact(s))", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Export failed: {e}", fg="red"))
        sys.exit(1)


# ── diff ─────────────────────────────────────────────────────────────────


@artifact_group.command("diff")
@click.argument("name")
@click.argument("version_a")
@click.argument("version_b")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
def artifact_diff(name: str, version_a: str, version_b: str, store_dir: str):
    """
    Show differences between two versions of an artifact.

    Examples:
      aq artifact diff my-config 1.0.0 1.1.0
    """
    from aquilia.artifacts import FilesystemArtifactStore, ArtifactReader

    store = FilesystemArtifactStore(store_dir)
    reader = ArtifactReader(store)

    a = store.load(name, version=version_a)
    b = store.load(name, version=version_b)

    if not a:
        click.echo(click.style(f"✗ Not found: {name}:{version_a}", fg="red"))
        sys.exit(1)
    if not b:
        click.echo(click.style(f"✗ Not found: {name}:{version_b}", fg="red"))
        sys.exit(1)

    diff_result = reader.diff(a, b)

    if not diff_result:
        click.echo(click.style("Artifacts are identical.", fg="green"))
        return

    click.echo(click.style(f"Diff: {name} {version_a} ↔ {version_b}", fg="cyan", bold=True))
    for key, change in diff_result.items():
        click.echo(f"  {key}: {change}")


# ── history ──────────────────────────────────────────────────────────────


@artifact_group.command("history")
@click.argument("name")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
def artifact_history(name: str, store_dir: str):
    """
    Show version history of an artifact.

    Examples:
      aq artifact history my-config
    """
    from aquilia.artifacts import FilesystemArtifactStore, ArtifactReader

    store = FilesystemArtifactStore(store_dir)
    reader = ArtifactReader(store)

    versions = reader.history(name)

    if not versions:
        click.echo(click.style(f"No history found for: {name}", fg="yellow"))
        return

    click.echo(click.style(f"History: {name}", fg="cyan", bold=True))
    for a in versions:
        digest_short = a.digest[:24] + "…" if len(a.digest) > 24 else a.digest
        created = a.created_at[:19] if a.created_at else "—"
        click.echo(f"  {a.version:<12} {digest_short:<28} {created}")


# ── import ───────────────────────────────────────────────────────────────


@artifact_group.command("import")
@click.argument("bundle_path")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
def artifact_import(bundle_path: str, store_dir: str):
    """
    Import artifacts from a bundle file.

    Examples:
      aq artifact import release.aq.json
      aq artifact import ./backup/bundle.aq.json --dir ./build/artifacts
    """
    from aquilia.artifacts import FilesystemArtifactStore

    store = FilesystemArtifactStore(store_dir)
    path = Path(bundle_path)

    if not path.exists():
        click.echo(click.style(f"✗ Bundle file not found: {bundle_path}", fg="red"))
        sys.exit(1)

    try:
        count = store.import_bundle(path)
        click.echo(click.style(f"✓ Imported {count} artifact(s) from {bundle_path}", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Import failed: {e}", fg="red"))
        sys.exit(1)


# ── count ────────────────────────────────────────────────────────────────


@artifact_group.command("count")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
@click.option("--kind", "-k", default="", help="Filter by artifact kind")
def artifact_count(store_dir: str, kind: str):
    """
    Count artifacts in the store.

    Examples:
      aq artifact count
      aq artifact count --kind model
    """
    from aquilia.artifacts import FilesystemArtifactStore

    store = FilesystemArtifactStore(store_dir)
    n = store.count(kind=kind)
    label = f" (kind={kind})" if kind else ""
    click.echo(f"{n} artifact(s){label}")


# ── stats ────────────────────────────────────────────────────────────────


@artifact_group.command("stats")
@click.option("--dir", "-d", "store_dir", default="artifacts", help="Artifact store directory")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def artifact_stats(store_dir: str, json_output: bool):
    """
    Show aggregate statistics for the artifact store.

    Examples:
      aq artifact stats
      aq artifact stats -j
    """
    from aquilia.artifacts import FilesystemArtifactStore, ArtifactReader

    store = FilesystemArtifactStore(store_dir)
    reader = ArtifactReader(store)
    info = reader.stats()

    if json_output:
        click.echo(json.dumps(info, indent=2, default=str))
        return

    click.echo(click.style("Artifact Store Statistics", fg="cyan", bold=True))
    click.echo(f"  Total:         {info['total']}")
    click.echo(f"  Unique names:  {info['unique_names']}")
    click.echo(f"  Total size:    {info['total_size_bytes']} bytes")
    click.echo(f"  Oldest:        {info['oldest'] or '—'}")
    click.echo(f"  Newest:        {info['newest'] or '—'}")
    if info.get("by_kind"):
        click.echo("  By kind:")
        for k, v in sorted(info["by_kind"].items()):
            click.echo(f"    {k}: {v}")
