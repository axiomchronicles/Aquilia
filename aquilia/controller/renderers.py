"""
Aquilia Content Negotiation & Renderer System.

Provides automatic content negotiation based on the ``Accept`` header,
plus a pluggable renderer architecture.

Built-in renderers:

- **JSONRenderer** — ``application/json`` (default)
- **XMLRenderer** — ``application/xml``
- **YAMLRenderer** — ``application/x-yaml``
- **PlainTextRenderer** — ``text/plain``
- **HTMLRenderer** — ``text/html``
- **MessagePackRenderer** — ``application/msgpack`` (optional)

Usage::

    from aquilia import Controller, GET
    from aquilia.controller.renderers import JSONRenderer, XMLRenderer

    class ProductsController(Controller):
        prefix = "/products"
        renderer_classes = [JSONRenderer, XMLRenderer]

        @GET("/")
        async def list_products(self, ctx):
            return products   # engine picks renderer from Accept header

Content negotiation order:
1. Explicit ``format`` query param: ``?format=xml``
2. ``Accept`` header negotiation (quality factors)
3. First renderer in the list (default)
"""

from __future__ import annotations

import html
import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

__all__ = [
    "BaseRenderer",
    "JSONRenderer",
    "XMLRenderer",
    "YAMLRenderer",
    "PlainTextRenderer",
    "HTMLRenderer",
    "MessagePackRenderer",
    "ContentNegotiator",
    "negotiate",
]


# ═══════════════════════════════════════════════════════════════════════════
#  Accept header parser
# ═══════════════════════════════════════════════════════════════════════════

def _parse_accept(header: str) -> List[Tuple[str, float]]:
    """
    Parse an ``Accept`` header into a list of ``(media_type, quality)``
    sorted by quality descending.

    Examples::

        _parse_accept("application/json")
        # → [("application/json", 1.0)]

        _parse_accept("text/html, application/json;q=0.9, */*;q=0.1")
        # → [("text/html", 1.0), ("application/json", 0.9), ("*/*", 0.1)]
    """
    if not header or not header.strip():
        return [("*/*", 1.0)]

    entries: List[Tuple[str, float]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        # Split media type and parameters
        segments = part.split(";")
        media = segments[0].strip()
        quality = 1.0
        for seg in segments[1:]:
            seg = seg.strip()
            if seg.startswith("q="):
                try:
                    quality = float(seg[2:])
                except (ValueError, TypeError):
                    quality = 1.0
        entries.append((media, quality))

    entries.sort(key=lambda x: x[1], reverse=True)
    return entries


def _media_matches(accept_type: str, renderer_type: str) -> bool:
    """
    Check if an Accept media type matches a renderer's media type.

    Supports wildcards: ``*/*``, ``application/*``.
    """
    if accept_type == "*/*":
        return True
    if "/" in accept_type and accept_type.endswith("/*"):
        prefix = accept_type.split("/")[0]
        return renderer_type.startswith(prefix + "/")
    return accept_type == renderer_type


# ═══════════════════════════════════════════════════════════════════════════
#  Base Renderer
# ═══════════════════════════════════════════════════════════════════════════

class BaseRenderer:
    """
    Abstract renderer.

    Subclass and set ``media_type``, ``format_suffix``, and implement
    ``render()``.
    """

    media_type: str = "application/octet-stream"
    format_suffix: str = ""          # e.g., "json", "xml"
    charset: Optional[str] = "utf-8"

    def render(
        self,
        data: Any,
        *,
        request: Any = None,
        response_status: int = 200,
        response_headers: Optional[Dict[str, str]] = None,
    ) -> Union[str, bytes]:
        """
        Render data to the target format.

        Returns str or bytes.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════
#  JSON Renderer
# ═══════════════════════════════════════════════════════════════════════════

class JSONRenderer(BaseRenderer):
    """Render data as JSON. Default renderer."""

    media_type = "application/json"
    format_suffix = "json"

    def __init__(self, *, indent: Optional[int] = None, ensure_ascii: bool = False):
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def render(self, data: Any, **kwargs) -> str:
        def _default(o):
            if isinstance(o, (set, tuple)):
                return list(o)
            if hasattr(o, "isoformat"):
                return o.isoformat()
            if hasattr(o, "to_dict"):
                return o.to_dict()
            if hasattr(o, "__dict__"):
                return {k: v for k, v in o.__dict__.items() if not k.startswith("_")}
            return str(o)

        return json.dumps(
            data,
            default=_default,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
        )


# ═══════════════════════════════════════════════════════════════════════════
#  XML Renderer
# ═══════════════════════════════════════════════════════════════════════════

class XMLRenderer(BaseRenderer):
    """
    Render data as XML.

    Converts dicts/lists to a simple XML structure with a configurable
    root element name.
    """

    media_type = "application/xml"
    format_suffix = "xml"

    def __init__(self, *, root_tag: str = "response", item_tag: str = "item"):
        self.root_tag = root_tag
        self.item_tag = item_tag

    def render(self, data: Any, **kwargs) -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append(f"<{self.root_tag}>")
        self._render_value(data, lines, indent=2)
        lines.append(f"</{self.root_tag}>")
        return "\n".join(lines)

    def _render_value(self, value: Any, lines: List[str], indent: int = 0):
        prefix = " " * indent
        if isinstance(value, dict):
            for k, v in value.items():
                tag = _sanitize_xml_tag(str(k))
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}<{tag}>")
                    self._render_value(v, lines, indent + 2)
                    lines.append(f"{prefix}</{tag}>")
                else:
                    escaped = html.escape(str(v)) if v is not None else ""
                    lines.append(f"{prefix}<{tag}>{escaped}</{tag}>")
        elif isinstance(value, (list, tuple)):
            for item in value:
                lines.append(f"{prefix}<{self.item_tag}>")
                self._render_value(item, lines, indent + 2)
                lines.append(f"{prefix}</{self.item_tag}>")
        else:
            escaped = html.escape(str(value)) if value is not None else ""
            lines.append(f"{prefix}{escaped}")


def _sanitize_xml_tag(tag: str) -> str:
    """Ensure a string is a valid XML tag name."""
    import re
    tag = re.sub(r"[^a-zA-Z0-9_.-]", "_", tag)
    if not tag or tag[0].isdigit():
        tag = "_" + tag
    return tag


# ═══════════════════════════════════════════════════════════════════════════
#  YAML Renderer
# ═══════════════════════════════════════════════════════════════════════════

class YAMLRenderer(BaseRenderer):
    """
    Render data as YAML.

    Requires ``pyyaml`` to be installed.
    """

    media_type = "application/x-yaml"
    format_suffix = "yaml"

    def render(self, data: Any, **kwargs) -> str:
        try:
            import yaml  # type: ignore[import-untyped]
            return yaml.dump(
                data,
                default_flow_style=False,
                allow_unicode=True,
            )
        except ImportError:
            # Fallback: manual simple YAML-like output
            return self._simple_yaml(data)

    def _simple_yaml(self, data: Any, indent: int = 0) -> str:
        """Minimal YAML formatter (no PyYAML dependency)."""
        prefix = "  " * indent
        lines: List[str] = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}{k}:")
                    lines.append(self._simple_yaml(v, indent + 1))
                else:
                    lines.append(f"{prefix}{k}: {v}")
        elif isinstance(data, (list, tuple)):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    lines.append(self._simple_yaml(item, indent + 1))
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  Plain Text Renderer
# ═══════════════════════════════════════════════════════════════════════════

class PlainTextRenderer(BaseRenderer):
    """Render data as plain text (str() conversion)."""

    media_type = "text/plain"
    format_suffix = "text"

    def render(self, data: Any, **kwargs) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, (dict, list)):
            return json.dumps(data, indent=2, default=str)
        return str(data)


# ═══════════════════════════════════════════════════════════════════════════
#  HTML Renderer
# ═══════════════════════════════════════════════════════════════════════════

class HTMLRenderer(BaseRenderer):
    """Render pre-built HTML strings (passthrough)."""

    media_type = "text/html"
    format_suffix = "html"

    def render(self, data: Any, **kwargs) -> str:
        if isinstance(data, str):
            return data
        # Auto-wrap non-string data in a minimal HTML page
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>Response</title></head><body>"
            f"<pre>{html.escape(json.dumps(data, indent=2, default=str))}</pre>"
            "</body></html>"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  MessagePack Renderer
# ═══════════════════════════════════════════════════════════════════════════

class MessagePackRenderer(BaseRenderer):
    """
    Render data as MessagePack binary (requires ``msgpack``).
    """

    media_type = "application/msgpack"
    format_suffix = "msgpack"
    charset = None  # binary

    def render(self, data: Any, **kwargs) -> bytes:
        try:
            import msgpack  # type: ignore[import-untyped]
            return msgpack.packb(data, use_bin_type=True, default=str)
        except ImportError:
            raise RuntimeError(
                "MessagePack rendering requires the 'msgpack' package. "
                "Install it with: pip install msgpack"
            )


# ═══════════════════════════════════════════════════════════════════════════
#  Content Negotiator
# ═══════════════════════════════════════════════════════════════════════════

class ContentNegotiator:
    """
    Select the best renderer for a request based on the ``Accept`` header
    and an optional ``?format=`` query parameter.

    Resolution order:
    1. ``?format=json`` → pick renderer whose ``format_suffix`` matches
    2. ``Accept`` header negotiation (quality-weighted)
    3. First renderer (default)
    """

    def __init__(self, renderers: Optional[Sequence[BaseRenderer]] = None):
        self.renderers: List[BaseRenderer] = list(renderers or [JSONRenderer()])

    def select_renderer(
        self,
        request: Any,
    ) -> Tuple[BaseRenderer, str]:
        """
        Return ``(renderer_instance, media_type)`` for the request.
        """
        # 1. Check ?format= override
        format_override = None
        if hasattr(request, "query_params"):
            qp = request.query_params
            format_override = (
                qp.get("format") if hasattr(qp, "get") else None
            )

        if format_override:
            for renderer in self.renderers:
                if renderer.format_suffix == format_override:
                    return renderer, renderer.media_type

        # 2. Accept header negotiation
        accept_header = ""
        if hasattr(request, "header"):
            accept_header = request.header("accept") or request.header("Accept") or "*/*"
        elif hasattr(request, "headers"):
            hdrs = request.headers
            if hasattr(hdrs, "get"):
                accept_header = hdrs.get("accept") or hdrs.get("Accept") or "*/*"
            else:
                accept_header = "*/*"
        else:
            accept_header = "*/*"

        parsed_accepts = _parse_accept(accept_header)

        for accept_type, quality in parsed_accepts:
            for renderer in self.renderers:
                if _media_matches(accept_type, renderer.media_type):
                    return renderer, renderer.media_type

        # 3. Default: first renderer
        default = self.renderers[0] if self.renderers else JSONRenderer()
        return default, default.media_type


# ═══════════════════════════════════════════════════════════════════════════
#  Convenience function
# ═══════════════════════════════════════════════════════════════════════════

def negotiate(
    data: Any,
    request: Any,
    *,
    renderers: Optional[Sequence[BaseRenderer]] = None,
    status: int = 200,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Union[str, bytes], str, int]:
    """
    One-shot content negotiation.

    Returns ``(rendered_body, content_type, status_code)``.
    """
    neg = ContentNegotiator(renderers=renderers)
    renderer, media_type = neg.select_renderer(request)

    body = renderer.render(
        data,
        request=request,
        response_status=status,
        response_headers=headers,
    )

    content_type = media_type
    if renderer.charset:
        content_type = f"{media_type}; charset={renderer.charset}"

    return body, content_type, status
