"""
AquilaCache CLI commands — ``aq cache`` group.

Commands:
    check     Validate cache configuration without starting the server.
    inspect   Show current cache configuration as JSON.
    stats     Display cache statistics (requires running server).
    clear     Clear all or namespace-scoped cache entries.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click


def _load_cache_config() -> dict:
    """Load cache config from workspace.py or config files."""
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
                return ws_dict.get("cache", ws_dict.get("integrations", {}).get("cache", {}))

    # Fallback to ConfigLoader
    from aquilia.config import ConfigLoader

    config = ConfigLoader()
    return config.get_cache_config()


def cmd_cache_check(verbose: bool = False) -> None:
    """Validate cache configuration."""
    config = _load_cache_config()

    if not config or not config.get("enabled", False):
        click.echo(click.style("✗ Cache integration is not enabled.", fg="yellow"))
        click.echo("  Add .integrate(Integration.cache(...)) to your workspace.py")
        return

    click.echo(click.style("Cache Configuration Check", fg="cyan", bold=True))
    click.echo("─" * 40)

    # Basic settings
    click.echo(f"  Enabled:          {config.get('enabled')}")
    click.echo(f"  Backend:          {config.get('backend', 'memory')}")
    click.echo(f"  Default TTL:      {config.get('default_ttl', 300)}s")
    click.echo(f"  Max Size:         {config.get('max_size', 10000)}")
    click.echo(f"  Eviction Policy:  {config.get('eviction_policy', 'lru')}")
    click.echo(f"  Serializer:       {config.get('serializer', 'json')}")
    click.echo(f"  Key Prefix:       {config.get('key_prefix', 'aq:')!r}")

    # Backend-specific
    backend = config.get("backend", "memory")
    if backend == "redis":
        redis_cfg = config.get("redis", {})
        click.echo()
        click.echo(click.style("  Redis Config:", fg="cyan"))
        url = redis_cfg.get("url", "redis://localhost:6379/0")
        click.echo(f"    URL:            {url}")
        click.echo(f"    Max Connections: {redis_cfg.get('max_connections', 10)}")
        click.echo(f"    Socket Timeout:  {redis_cfg.get('socket_timeout', 5)}s")

        # Try ping
        click.echo()
        click.echo("  Testing Redis connection...")
        try:
            import redis as _redis

            r = _redis.from_url(url, socket_timeout=3)
            r.ping()
            click.echo(click.style("  ✓ Redis connection OK", fg="green"))
            info = r.info("memory")
            click.echo(f"    Used Memory: {info.get('used_memory_human', 'N/A')}")
            r.close()
        except ImportError:
            click.echo(click.style("  ✗ redis package not installed", fg="red"))
            click.echo("    pip install redis")
        except Exception as e:
            click.echo(click.style(f"  ✗ Redis connection failed: {e}", fg="red"))

    elif backend == "composite":
        click.echo()
        click.echo(click.style("  Composite (L1 + L2):", fg="cyan"))
        l1 = config.get("memory", {})
        click.echo(f"    L1 Max Size:     {l1.get('max_size', 1000)}")
        click.echo(f"    L1 TTL:          {l1.get('default_ttl', 60)}s")
        redis_cfg = config.get("redis", {})
        click.echo(f"    L2 Redis URL:    {redis_cfg.get('url', 'redis://localhost:6379/0')}")

    # Middleware
    mw_cfg = config.get("middleware", {})
    click.echo()
    click.echo(f"  Middleware:        {'enabled' if mw_cfg.get('enabled') else 'disabled'}")
    if mw_cfg.get("enabled"):
        click.echo(f"    HTTP TTL:       {mw_cfg.get('ttl', 300)}s")
        click.echo(f"    Namespace:      {mw_cfg.get('namespace', 'http')!r}")

    click.echo()
    click.echo(click.style("✓ Cache configuration valid", fg="green"))


def cmd_cache_inspect(verbose: bool = False) -> None:
    """Display cache config as JSON."""
    config = _load_cache_config()
    if not config:
        click.echo("{}")
        return
    indent = 2 if verbose else None
    click.echo(json.dumps(config, indent=indent, default=str))


def cmd_cache_stats(verbose: bool = False) -> None:
    """Display cache statistics from trace diagnostics."""
    trace_path = Path(".aquilia/diagnostics.json")
    if not trace_path.exists():
        click.echo(click.style("✗ No diagnostics found.", fg="yellow"))
        click.echo("  Start the server first to generate trace data.")
        return

    try:
        data = json.loads(trace_path.read_text())
    except Exception as e:
        click.echo(click.style(f"✗ Failed to read diagnostics: {e}", fg="red"))
        return

    cache_data = data.get("cache", {})
    if not cache_data.get("active", False):
        click.echo(click.style("✗ Cache subsystem is not active.", fg="yellow"))
        return

    click.echo(click.style("Cache Statistics", fg="cyan", bold=True))
    click.echo("─" * 40)
    click.echo(f"  Service:         {cache_data.get('service', 'N/A')}")
    click.echo(f"  Backend:         {cache_data.get('backend', 'N/A')}")
    click.echo(f"  Default TTL:     {cache_data.get('default_ttl', 'N/A')}s")
    click.echo(f"  Max Size:        {cache_data.get('max_size', 'N/A')}")
    click.echo(f"  Eviction Policy: {cache_data.get('eviction_policy', 'N/A')}")


def cmd_cache_clear(namespace: Optional[str] = None, verbose: bool = False) -> None:
    """
    Clear cache entries.

    This creates a temporary CacheService from config and clears it.
    Works only for in-process memory caches or reachable Redis.
    """
    config = _load_cache_config()
    if not config or not config.get("enabled", False):
        click.echo(click.style("✗ Cache is not enabled.", fg="yellow"))
        return

    try:
        from aquilia.cache.di_providers import build_cache_config, create_cache_service

        cfg = build_cache_config(config)
        svc = create_cache_service(cfg)

        async def _clear():
            await svc.initialize()
            if namespace:
                await svc.invalidate_namespace(namespace)
                click.echo(click.style(f"✓ Cleared namespace '{namespace}'", fg="green"))
            else:
                await svc.clear()
                click.echo(click.style("✓ Cache cleared", fg="green"))
            await svc.shutdown()

        asyncio.run(_clear())
    except Exception as e:
        click.echo(click.style(f"✗ Cache clear failed: {e}", fg="red"))
        if verbose:
            import traceback
            traceback.print_exc()
