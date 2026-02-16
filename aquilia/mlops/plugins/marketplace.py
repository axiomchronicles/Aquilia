"""
Plugin marketplace — lightweight discovery & installation of community
and first-party MLOps plugins from a remote index.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aquilia.mlops.plugins.marketplace")

# Default index URL (can be overridden)
DEFAULT_INDEX_URL = "https://plugins.aquilia.dev/v1/index.json"


@dataclass(frozen=True)
class MarketplaceEntry:
    name: str
    version: str
    description: str
    author: str
    pypi_name: str  # pip-installable package name
    homepage: str = ""
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    verified: bool = False


class PluginMarketplace:
    """
    Browse and install plugins from a remote JSON index.

    The index is a plain JSON array of :class:`MarketplaceEntry` objects
    served from a static URL (CDN, S3, GitHub Pages, etc.).

    For air-gapped / on-prem installs the index can be a local file path.
    """

    def __init__(self, index_url: str = DEFAULT_INDEX_URL) -> None:
        self._index_url = index_url
        self._cache: Optional[List[MarketplaceEntry]] = None

    # ── index operations ─────────────────────────────────────────────────

    async def fetch_index(self) -> List[MarketplaceEntry]:
        """
        Download the plugin index.

        Falls back to a local file if the URL starts with ``file://`` or
        is a plain filesystem path.
        """
        import urllib.request

        raw: str
        if self._index_url.startswith("file://") or not self._index_url.startswith(
            "http"
        ):
            path = self._index_url.removeprefix("file://")
            with open(path) as f:
                raw = f.read()
        else:
            # simple stdlib fetch — no aiohttp dependency needed
            with urllib.request.urlopen(self._index_url, timeout=10) as resp:
                raw = resp.read().decode()

        entries = [
            MarketplaceEntry(**item)
            for item in json.loads(raw)
        ]
        self._cache = entries
        logger.info("Fetched %d plugins from marketplace index", len(entries))
        return entries

    def search(
        self,
        query: str,
        *,
        tags: Optional[List[str]] = None,
        verified_only: bool = False,
    ) -> List[MarketplaceEntry]:
        """
        Search the cached index.

        Call :meth:`fetch_index` first to populate the cache.
        """
        if self._cache is None:
            raise RuntimeError("Call fetch_index() before search()")

        q = query.lower()
        results: List[MarketplaceEntry] = []

        for entry in self._cache:
            if verified_only and not entry.verified:
                continue
            if tags and not set(tags) & set(entry.tags):
                continue
            if (
                q in entry.name.lower()
                or q in entry.description.lower()
                or q in entry.author.lower()
            ):
                results.append(entry)

        return sorted(results, key=lambda e: e.downloads, reverse=True)

    # ── install ──────────────────────────────────────────────────────────

    def install(self, entry_or_name: MarketplaceEntry | str) -> bool:
        """
        Install a plugin via pip.

        Accepts either a :class:`MarketplaceEntry` or a PyPI package name.
        """
        if isinstance(entry_or_name, MarketplaceEntry):
            pkg = entry_or_name.pypi_name
        else:
            pkg = entry_or_name

        logger.info("Installing plugin package '%s'...", pkg)
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info("Successfully installed '%s'", pkg)
            return True
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to install '%s': %s", pkg, exc)
            return False

    def uninstall(self, pypi_name: str) -> bool:
        """Uninstall a plugin package."""
        logger.info("Uninstalling plugin package '%s'...", pypi_name)
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "uninstall", "-y", pypi_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info("Successfully uninstalled '%s'", pypi_name)
            return True
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to uninstall '%s': %s", pypi_name, exc)
            return False
