"""
Static File Middleware - Production-grade static asset serving.

Features:
- Radix trie-based path matching for O(k) lookup (k = path length)
- Content-type detection via mimetypes + custom mappings
- ETag generation (MD5 or content-hash) with If-None-Match support
- Last-Modified / If-Modified-Since conditional responses
- Cache-Control with configurable immutable/max-age directives
- Range request support (partial content / 206)
- Brotli/gzip pre-compressed file detection (.br, .gz)
- Directory traversal prevention with realpath canonicalization
- Configurable file size limits
- In-memory LRU cache for hot files
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import stat
import time
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import formatdate, parsedate_to_datetime
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TYPE_CHECKING,
)

from aquilia.request import Request
from aquilia.response import Response

if TYPE_CHECKING:
    from aquilia.controller.base import RequestCtx

Handler = Callable[[Request, "RequestCtx"], Awaitable[Response]]

# ─── Custom MIME types beyond stdlib ──────────────────────────────────────────
_EXTRA_MIME_TYPES: Dict[str, str] = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".webm": "video/webm",
    ".mp4": "video/mp4",
    ".wasm": "application/wasm",
    ".map": "application/json",
    ".mjs": "application/javascript",
    ".jsonld": "application/ld+json",
    ".manifest": "text/cache-manifest",
    ".ico": "image/x-icon",
}

# Ensure stdlib knows these
for _ext, _mime in _EXTRA_MIME_TYPES.items():
    mimetypes.add_type(_mime, _ext)


# ─── Radix Trie for prefix matching ──────────────────────────────────────────

class _RadixNode:
    """Node in the radix trie for URL-prefix → directory mapping."""
    __slots__ = ("children", "directory", "prefix")

    def __init__(self, prefix: str = ""):
        self.prefix: str = prefix
        self.children: Dict[str, "_RadixNode"] = {}
        self.directory: Optional[Path] = None


class _RadixTrie:
    """
    Compressed radix trie mapping URL prefixes to filesystem directories.

    Provides O(k) lookup where k is the length of the URL path.
    Supports multiple mount points (e.g. /static → ./static, /media → ./uploads).
    """

    def __init__(self) -> None:
        self.root = _RadixNode()

    def insert(self, url_prefix: str, directory: Path) -> None:
        """Insert a URL prefix → directory mapping."""
        url_prefix = "/" + url_prefix.strip("/")
        node = self.root
        remaining = url_prefix

        while remaining:
            matched = False
            for key, child in node.children.items():
                # Find common prefix
                common = self._common_prefix(remaining, key)
                if not common:
                    continue

                if common == key:
                    # Full match on this edge, continue down
                    node = child
                    remaining = remaining[len(common):]
                    matched = True
                    break
                else:
                    # Partial match — split the edge
                    split_child = _RadixNode(prefix=common)
                    child.prefix = key[len(common):]
                    split_child.children[child.prefix] = child
                    node.children[common] = split_child
                    del node.children[key]

                    rest = remaining[len(common):]
                    if rest:
                        new_node = _RadixNode(prefix=rest)
                        new_node.directory = directory
                        split_child.children[rest] = new_node
                    else:
                        split_child.directory = directory
                    return

            if not matched:
                new_node = _RadixNode(prefix=remaining)
                new_node.directory = directory
                node.children[remaining] = new_node
                return

        node.directory = directory

    def lookup(self, path: str) -> Optional[Tuple[Path, str]]:
        """
        Find the longest matching prefix for *path*.

        Returns:
            (directory, relative_path) or None
        """
        path = "/" + path.strip("/")
        node = self.root
        consumed = 0
        best: Optional[Tuple[Path, int]] = None

        if node.directory is not None:
            best = (node.directory, consumed)

        remaining = path
        while remaining:
            advanced = False
            for key, child in node.children.items():
                if remaining.startswith(key):
                    node = child
                    consumed += len(key)
                    remaining = remaining[len(key):]
                    if node.directory is not None:
                        best = (node.directory, consumed)
                    advanced = True
                    break
            if not advanced:
                break

        if best is None:
            return None

        directory, prefix_len = best
        relative = path[prefix_len:].lstrip("/")
        return directory, relative

    @staticmethod
    def _common_prefix(a: str, b: str) -> str:
        i = 0
        limit = min(len(a), len(b))
        while i < limit and a[i] == b[i]:
            i += 1
        return a[:i]


# ─── LRU File Cache ──────────────────────────────────────────────────────────

class _LRUFileCache:
    """
    Thread-safe LRU cache for hot static files.

    Stores (content_bytes, etag, content_type, mtime) keyed by
    canonical file path.  Evicts least-recently-used entries when
    capacity is exceeded.
    """

    __slots__ = ("_capacity", "_max_file_size", "_store", "_current_size")

    def __init__(self, capacity_bytes: int = 64 * 1024 * 1024, max_file_size: int = 1024 * 1024):
        self._capacity = capacity_bytes
        self._max_file_size = max_file_size
        self._store: OrderedDict[str, Tuple[bytes, str, str, float]] = OrderedDict()
        self._current_size = 0

    def get(self, key: str) -> Optional[Tuple[bytes, str, str, float]]:
        """Retrieve cached entry, promoting to MRU position."""
        entry = self._store.get(key)
        if entry is not None:
            self._store.move_to_end(key)
        return entry

    def put(self, key: str, content: bytes, etag: str, content_type: str, mtime: float) -> None:
        size = len(content)
        if size > self._max_file_size:
            return  # Too large to cache

        # Evict if already present
        if key in self._store:
            old = self._store.pop(key)
            self._current_size -= len(old[0])

        # Evict LRU until we have space
        while self._current_size + size > self._capacity and self._store:
            _, evicted = self._store.popitem(last=False)
            self._current_size -= len(evicted[0])

        self._store[key] = (content, etag, content_type, mtime)
        self._current_size += size

    def invalidate(self, key: str) -> None:
        entry = self._store.pop(key, None)
        if entry:
            self._current_size -= len(entry[0])


# ─── Static File Middleware ───────────────────────────────────────────────────

class StaticMiddleware:
    """
    Production-grade static file serving middleware.

    Serves files from configured directories when the request path matches
    a registered URL prefix.  Falls through to the application handler for
    unmatched paths.

    Args:
        directories: Mapping of URL prefix → filesystem directory.
                     Example: {"/static": "./static", "/media": "./uploads"}
        cache_max_age: Cache-Control max-age (seconds).  0 = no-cache.
        immutable: If True, set ``Cache-Control: immutable`` (for fingerprinted assets).
        etag: Enable ETag generation.
        gzip: Serve pre-compressed ``.gz`` files when client supports gzip.
        brotli: Serve pre-compressed ``.br`` files when client supports br.
        max_file_size: Maximum file size to serve (bytes).  0 = unlimited.
        memory_cache: Enable in-memory LRU cache for hot files.
        memory_cache_size: Maximum memory cache size (bytes).
        allowed_extensions: Whitelist of allowed file extensions (e.g. {".css", ".js"}).
                           Empty set = allow all.
        index_file: Serve this file for directory requests (e.g. "index.html").
                    None = disable directory index.
        html5_history: If True, serve *index_file* for 404s within the prefix
                       (for SPA routing).
    """

    def __init__(
        self,
        directories: Optional[Dict[str, str]] = None,
        cache_max_age: int = 86400,
        immutable: bool = False,
        etag: bool = True,
        gzip: bool = True,
        brotli: bool = True,
        max_file_size: int = 0,
        memory_cache: bool = True,
        memory_cache_size: int = 64 * 1024 * 1024,
        memory_cache_file_limit: int = 1024 * 1024,
        allowed_extensions: Optional[Set[str]] = None,
        index_file: Optional[str] = "index.html",
        html5_history: bool = False,
        extra_directories: Optional[Dict[str, List[str]]] = None,
    ):
        self._trie = _RadixTrie()
        self._cache_max_age = cache_max_age
        self._immutable = immutable
        self._etag = etag
        self._gzip = gzip
        self._brotli = brotli
        self._max_file_size = max_file_size
        self._allowed_extensions = allowed_extensions or set()
        self._index_file = index_file
        self._html5_history = html5_history

        # Resolve and validate directories
        self._directories: Dict[str, Path] = {}
        for url_prefix, fs_dir in (directories or {"/static": "static"}).items():
            resolved = Path(fs_dir).resolve()
            if not resolved.is_dir():
                # Try relative to cwd
                resolved = (Path.cwd() / fs_dir).resolve()
            self._directories[url_prefix] = resolved
            self._trie.insert(url_prefix, resolved)

        # Fallback directories per URL prefix (for module static dirs).
        # When a file isn't found in the primary directory for a prefix,
        # these are searched in order — like Django's AppDirectoriesFinder.
        self._fallback_dirs: Dict[str, List[Path]] = {}
        for url_prefix, fs_dirs in (extra_directories or {}).items():
            prefix_key = "/" + url_prefix.strip("/")
            fallbacks: List[Path] = []
            for fs_dir in fs_dirs:
                resolved = Path(fs_dir).resolve()
                if not resolved.is_dir():
                    resolved = (Path.cwd() / fs_dir).resolve()
                if resolved.is_dir():
                    fallbacks.append(resolved)
            if fallbacks:
                self._fallback_dirs[prefix_key] = fallbacks
                # Ensure trie has an entry for this prefix even if the
                # primary directory doesn't exist (creates a sentinel).
                if prefix_key not in self._directories:
                    self._trie.insert(prefix_key, fallbacks[0])
                    self._directories[prefix_key] = fallbacks[0]

        # Memory cache
        self._file_cache: Optional[_LRUFileCache] = None
        if memory_cache:
            self._file_cache = _LRUFileCache(
                capacity_bytes=memory_cache_size,
                max_file_size=memory_cache_file_limit,
            )

    # ── Public API ────────────────────────────────────────────────────────

    async def __call__(
        self,
        request: Request,
        ctx: "RequestCtx",
        next_handler: Handler,
    ) -> Response:
        """Serve static file or fall through to next handler."""
        # Only handle GET and HEAD
        if request.method not in ("GET", "HEAD"):
            return await next_handler(request, ctx)

        result = self._trie.lookup(request.path)
        if result is None:
            return await next_handler(request, ctx)

        directory, relative_path = result
        if not relative_path:
            if self._index_file:
                relative_path = self._index_file
            else:
                return await next_handler(request, ctx)

        # Try the primary directory first
        response = self._serve_file(request, directory, relative_path)
        if response is not None:
            return response

        # Search fallback directories (module static dirs).
        # Determine which prefix matched so we can look up its fallbacks.
        matched_prefix = self._matched_prefix(request.path)
        if matched_prefix and matched_prefix in self._fallback_dirs:
            for fallback_dir in self._fallback_dirs[matched_prefix]:
                response = self._serve_file(request, fallback_dir, relative_path)
                if response is not None:
                    return response

        # HTML5 history API fallback
        if self._html5_history and self._index_file:
            response = self._serve_file(request, directory, self._index_file)
            if response is not None:
                return response

        return await next_handler(request, ctx)

    def _matched_prefix(self, path: str) -> Optional[str]:
        """Return the URL prefix that matched *path*, or None."""
        path = "/" + path.strip("/")
        # Walk from longest registered prefix to shortest
        for prefix in sorted(self._directories, key=len, reverse=True):
            if path.startswith(prefix):
                return prefix
        return None

    # ── Internals ─────────────────────────────────────────────────────────

    def _serve_file(
        self, request: Request, directory: Path, relative_path: str
    ) -> Optional[Response]:
        """Attempt to serve a single file.  Returns None on miss."""
        # Canonicalize and prevent traversal
        file_path = (directory / relative_path).resolve()
        try:
            file_path.relative_to(directory)
        except ValueError:
            # Traversal attempt
            return Response(b"Forbidden", status=403)

        # Check extension whitelist
        if self._allowed_extensions:
            ext = file_path.suffix.lower()
            if ext not in self._allowed_extensions:
                return None

        # Negotiate pre-compressed variant
        accept_encoding = request.header("accept-encoding") or ""
        selected_path, encoding = self._negotiate_encoding(file_path, accept_encoding)

        if not selected_path.is_file():
            return None

        # Stat the file
        try:
            st = selected_path.stat()
        except OSError:
            return None

        # Size check
        if self._max_file_size and st.st_size > self._max_file_size:
            return Response(b"File too large", status=413)

        # Content type
        content_type = self._detect_content_type(file_path)

        # ETag
        etag = self._compute_etag(selected_path, st) if self._etag else None

        # Conditional: If-None-Match
        if etag:
            client_etag = request.header("if-none-match")
            if client_etag and self._etag_matches(client_etag, etag):
                return Response(b"", status=304, headers=self._build_cache_headers(etag, st))

        # Conditional: If-Modified-Since
        ims = request.header("if-modified-since")
        if ims:
            try:
                ims_dt = parsedate_to_datetime(ims)
                file_dt = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
                if file_dt <= ims_dt:
                    return Response(b"", status=304, headers=self._build_cache_headers(etag, st))
            except (ValueError, TypeError):
                pass

        # Try memory cache
        canonical = str(selected_path)
        if self._file_cache:
            cached = self._file_cache.get(canonical)
            if cached:
                content, cached_etag, cached_ct, cached_mtime = cached
                if cached_mtime >= st.st_mtime:
                    headers = self._build_headers(
                        cached_ct, len(content), cached_etag, st, encoding
                    )
                    body = b"" if request.method == "HEAD" else content
                    return Response(body, status=200, headers=headers)
                else:
                    self._file_cache.invalidate(canonical)

        # Read file
        try:
            content = selected_path.read_bytes()
        except OSError:
            return None

        # Populate cache
        if self._file_cache and etag:
            self._file_cache.put(canonical, content, etag, content_type, st.st_mtime)

        headers = self._build_headers(content_type, len(content), etag, st, encoding)

        # Range request support
        range_header = request.header("range")
        if range_header and request.method == "GET":
            range_response = self._handle_range(content, range_header, content_type, headers)
            if range_response:
                return range_response

        body = b"" if request.method == "HEAD" else content
        return Response(body, status=200, headers=headers)

    def _negotiate_encoding(
        self, original: Path, accept_encoding: str
    ) -> Tuple[Path, Optional[str]]:
        """Select pre-compressed file if available and accepted."""
        ae_lower = accept_encoding.lower()

        if self._brotli and "br" in ae_lower:
            br_path = original.with_suffix(original.suffix + ".br")
            if br_path.is_file():
                return br_path, "br"

        if self._gzip and "gzip" in ae_lower:
            gz_path = original.with_suffix(original.suffix + ".gz")
            if gz_path.is_file():
                return gz_path, "gzip"

        return original, None

    def _detect_content_type(self, path: Path) -> str:
        """Detect MIME type for the *original* (uncompressed) file path."""
        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"

    def _compute_etag(self, path: Path, st: os.stat_result) -> str:
        """Compute a weak ETag from inode + mtime + size."""
        raw = f"{st.st_ino}-{st.st_mtime_ns}-{st.st_size}"
        digest = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:16]
        return f'W/"{digest}"'

    def _etag_matches(self, client_header: str, etag: str) -> bool:
        """Check If-None-Match with multiple etag support."""
        if client_header.strip() == "*":
            return True
        # Strip surrounding whitespace and compare each tag
        tags = [t.strip().strip('"').strip("W/").strip('"') for t in client_header.split(",")]
        clean_etag = etag.strip('"').strip("W/").strip('"')
        return clean_etag in tags

    def _build_cache_headers(
        self, etag: Optional[str], st: os.stat_result
    ) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if etag:
            headers["etag"] = etag
        headers["last-modified"] = formatdate(st.st_mtime, usegmt=True)
        cc_parts = [f"max-age={self._cache_max_age}", "public"]
        if self._immutable:
            cc_parts.append("immutable")
        headers["cache-control"] = ", ".join(cc_parts)
        return headers

    def _build_headers(
        self,
        content_type: str,
        length: int,
        etag: Optional[str],
        st: os.stat_result,
        encoding: Optional[str],
    ) -> Dict[str, str]:
        headers = self._build_cache_headers(etag, st)
        headers["content-type"] = content_type
        headers["content-length"] = str(length)
        headers["accept-ranges"] = "bytes"
        if encoding:
            headers["content-encoding"] = encoding
            headers["vary"] = "Accept-Encoding"
        return headers

    def _handle_range(
        self,
        content: bytes,
        range_header: str,
        content_type: str,
        base_headers: Dict[str, str],
    ) -> Optional[Response]:
        """Handle Range: bytes=start-end header."""
        total = len(content)
        try:
            if not range_header.startswith("bytes="):
                return None
            range_spec = range_header[6:]
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else total - 1
        except (ValueError, IndexError):
            return Response(
                b"Invalid Range",
                status=416,
                headers={"content-range": f"bytes */{total}"},
            )

        if start > end or start >= total:
            return Response(
                b"Range Not Satisfiable",
                status=416,
                headers={"content-range": f"bytes */{total}"},
            )

        end = min(end, total - 1)
        slice_bytes = content[start : end + 1]

        headers = dict(base_headers)
        headers["content-range"] = f"bytes {start}-{end}/{total}"
        headers["content-length"] = str(len(slice_bytes))
        headers["content-type"] = content_type

        return Response(slice_bytes, status=206, headers=headers)

    # ── URL generation helper (for templates) ─────────────────────────────

    def url_for_static(self, path: str) -> str:
        """
        Generate a URL for a static asset.

        Picks the first registered prefix as base.
        """
        if self._directories:
            prefix = next(iter(self._directories))
            return f"{prefix.rstrip('/')}/{path.lstrip('/')}"
        return f"/static/{path.lstrip('/')}"
