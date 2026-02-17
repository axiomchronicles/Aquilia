"""
Aquilia Pagination System — Django-REST-style pagination backends.

Provides three pagination strategies out of the box:

- **PageNumberPagination** — ``?page=2&page_size=20``
- **LimitOffsetPagination** — ``?limit=20&offset=40``
- **CursorPagination** — ``?cursor=<opaque>`` (keyset / seek pagination)

Each paginator works with both ORM QuerySets and plain lists.

Usage (declarative on route)::

    from aquilia import Controller, GET
    from aquilia.controller.pagination import PageNumberPagination

    class ProductsController(Controller):
        prefix = "/products"

        @GET("/", pagination_class=PageNumberPagination)
        async def list_products(self, ctx):
            return await Product.objects.all()  # engine paginates

Usage (explicit in handler)::

    paginator = PageNumberPagination(page_size=25)
    page = paginator.paginate_list(products, request)
    # page == {"count": 1200, "next": "...", "previous": "...", "results": [...]}
"""

from __future__ import annotations

import base64
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse


__all__ = [
    "BasePagination",
    "PageNumberPagination",
    "LimitOffsetPagination",
    "CursorPagination",
    "NoPagination",
]


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _build_url(request: Any, params: Dict[str, Any]) -> Optional[str]:
    """Build an absolute URL from the current request with updated query params."""
    try:
        # Get base URL components
        scheme = "http"
        host = "localhost"
        path = "/"

        if hasattr(request, "scope"):
            scope = request.scope
            scheme = scope.get("scheme", "http")
            # Build host from scope headers
            headers = dict(scope.get("headers", []))
            host_header = headers.get(b"host", b"localhost").decode("utf-8")
            host = host_header
            path = scope.get("path", "/")
        elif hasattr(request, "path"):
            path = request.path

        # Build query string from params
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        return f"{scheme}://{host}{path}?{qs}" if qs else f"{scheme}://{host}{path}"
    except Exception:
        # Fallback: relative URL
        qs = urlencode({k: v for k, v in params.items() if v is not None})
        path = getattr(request, "path", "/")
        return f"{path}?{qs}" if qs else path


def _get_current_params(request: Any) -> Dict[str, str]:
    """Extract current query parameters as a flat dict."""
    if hasattr(request, "query_params"):
        qp = request.query_params
        if hasattr(qp, "items"):
            return dict(qp.items())
        return dict(qp) if qp else {}
    return {}


# ═══════════════════════════════════════════════════════════════════════════
#  Base class
# ═══════════════════════════════════════════════════════════════════════════

class BasePagination:
    """
    Abstract base for pagination backends.

    Subclasses must implement ``paginate_list`` and optionally
    ``paginate_queryset`` (async, for ORM querysets).
    """

    def paginate_list(
        self,
        data: List[Any],
        request: Any,
    ) -> Dict[str, Any]:
        """
        Paginate an in-memory list.

        Returns a dict with pagination envelope:
        ``{"count": ..., "next": ..., "previous": ..., "results": [...]}``
        """
        raise NotImplementedError

    async def paginate_queryset(
        self,
        queryset: Any,
        request: Any,
    ) -> Dict[str, Any]:
        """
        Paginate an ORM queryset.

        Default implementation fetches all() and delegates to paginate_list.
        """
        items = await queryset.all()
        serialized = [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in items
        ]
        return self.paginate_list(serialized, request)


class NoPagination(BasePagination):
    """Passthrough — no pagination applied."""

    def paginate_list(self, data: List[Any], request: Any) -> Dict[str, Any]:
        return {
            "count": len(data),
            "next": None,
            "previous": None,
            "results": data,
        }


# ═══════════════════════════════════════════════════════════════════════════
#  PageNumberPagination
# ═══════════════════════════════════════════════════════════════════════════

class PageNumberPagination(BasePagination):
    """
    Classic page-number pagination.

    Query params: ``?page=2&page_size=20``

    Response envelope::

        {
            "count": 1200,
            "total_pages": 60,
            "page": 2,
            "page_size": 20,
            "next": "http://host/items/?page=3&page_size=20",
            "previous": "http://host/items/?page=1&page_size=20",
            "results": [...]
        }

    Class-level config::

        class LargePagePagination(PageNumberPagination):
            page_size = 100
            max_page_size = 500
    """

    page_size: int = 20
    max_page_size: int = 1000
    page_param: str = "page"
    page_size_param: str = "page_size"

    def __init__(
        self,
        page_size: Optional[int] = None,
        max_page_size: Optional[int] = None,
    ):
        if page_size is not None:
            self.page_size = page_size
        if max_page_size is not None:
            self.max_page_size = max_page_size

    def _parse_page(self, request: Any) -> tuple:
        """Return (page_number, page_size) from request params."""
        params = _get_current_params(request)
        try:
            page = max(1, int(params.get(self.page_param, 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            size = int(params.get(self.page_size_param, self.page_size))
            size = max(1, min(size, self.max_page_size))
        except (ValueError, TypeError):
            size = self.page_size
        return page, size

    def paginate_list(
        self,
        data: List[Any],
        request: Any,
    ) -> Dict[str, Any]:
        page, size = self._parse_page(request)
        total = len(data)
        total_pages = max(1, math.ceil(total / size))

        start = (page - 1) * size
        end = start + size
        results = data[start:end]

        # Build navigation URLs
        base_params = _get_current_params(request)
        base_params.pop(self.page_param, None)
        base_params.pop(self.page_size_param, None)

        next_url = None
        if page < total_pages:
            next_params = {**base_params, self.page_param: page + 1, self.page_size_param: size}
            next_url = _build_url(request, next_params)

        prev_url = None
        if page > 1:
            prev_params = {**base_params, self.page_param: page - 1, self.page_size_param: size}
            prev_url = _build_url(request, prev_params)

        return {
            "count": total,
            "total_pages": total_pages,
            "page": page,
            "page_size": size,
            "next": next_url,
            "previous": prev_url,
            "results": results,
        }

    async def paginate_queryset(
        self,
        queryset: Any,
        request: Any,
    ) -> Dict[str, Any]:
        """
        Optimised ORM pagination — uses .count() + .offset().limit()
        instead of fetching all rows.
        """
        page, size = self._parse_page(request)

        # Count total
        try:
            total = await queryset.count()
        except Exception:
            # Fallback to list-based
            return await super().paginate_queryset(queryset, request)

        total_pages = max(1, math.ceil(total / size))
        offset = (page - 1) * size

        try:
            items = await queryset.offset(offset).limit(size).all()
            results = [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in items
            ]
        except Exception:
            return await super().paginate_queryset(queryset, request)

        base_params = _get_current_params(request)
        base_params.pop(self.page_param, None)
        base_params.pop(self.page_size_param, None)

        next_url = None
        if page < total_pages:
            next_params = {**base_params, self.page_param: page + 1, self.page_size_param: size}
            next_url = _build_url(request, next_params)

        prev_url = None
        if page > 1:
            prev_params = {**base_params, self.page_param: page - 1, self.page_size_param: size}
            prev_url = _build_url(request, prev_params)

        return {
            "count": total,
            "total_pages": total_pages,
            "page": page,
            "page_size": size,
            "next": next_url,
            "previous": prev_url,
            "results": results,
        }


# ═══════════════════════════════════════════════════════════════════════════
#  LimitOffsetPagination
# ═══════════════════════════════════════════════════════════════════════════

class LimitOffsetPagination(BasePagination):
    """
    Limit/Offset pagination.

    Query params: ``?limit=20&offset=40``

    Response envelope::

        {
            "count": 1200,
            "limit": 20,
            "offset": 40,
            "next": "http://host/items/?limit=20&offset=60",
            "previous": "http://host/items/?limit=20&offset=20",
            "results": [...]
        }
    """

    default_limit: int = 20
    max_limit: int = 1000
    limit_param: str = "limit"
    offset_param: str = "offset"

    def __init__(
        self,
        default_limit: Optional[int] = None,
        max_limit: Optional[int] = None,
    ):
        if default_limit is not None:
            self.default_limit = default_limit
        if max_limit is not None:
            self.max_limit = max_limit

    def _parse_params(self, request: Any) -> tuple:
        params = _get_current_params(request)
        try:
            limit = int(params.get(self.limit_param, self.default_limit))
            limit = max(1, min(limit, self.max_limit))
        except (ValueError, TypeError):
            limit = self.default_limit
        try:
            offset = max(0, int(params.get(self.offset_param, 0)))
        except (ValueError, TypeError):
            offset = 0
        return limit, offset

    def paginate_list(
        self,
        data: List[Any],
        request: Any,
    ) -> Dict[str, Any]:
        limit, offset = self._parse_params(request)
        total = len(data)
        results = data[offset: offset + limit]

        base_params = _get_current_params(request)
        base_params.pop(self.limit_param, None)
        base_params.pop(self.offset_param, None)

        next_url = None
        if offset + limit < total:
            next_params = {**base_params, self.limit_param: limit, self.offset_param: offset + limit}
            next_url = _build_url(request, next_params)

        prev_url = None
        if offset > 0:
            prev_offset = max(0, offset - limit)
            prev_params = {**base_params, self.limit_param: limit, self.offset_param: prev_offset}
            prev_url = _build_url(request, prev_params)

        return {
            "count": total,
            "limit": limit,
            "offset": offset,
            "next": next_url,
            "previous": prev_url,
            "results": results,
        }

    async def paginate_queryset(
        self,
        queryset: Any,
        request: Any,
    ) -> Dict[str, Any]:
        limit, offset = self._parse_params(request)

        try:
            total = await queryset.count()
        except Exception:
            return await super().paginate_queryset(queryset, request)

        try:
            items = await queryset.offset(offset).limit(limit).all()
            results = [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in items
            ]
        except Exception:
            return await super().paginate_queryset(queryset, request)

        base_params = _get_current_params(request)
        base_params.pop(self.limit_param, None)
        base_params.pop(self.offset_param, None)

        next_url = None
        if offset + limit < total:
            next_params = {**base_params, self.limit_param: limit, self.offset_param: offset + limit}
            next_url = _build_url(request, next_params)

        prev_url = None
        if offset > 0:
            prev_offset = max(0, offset - limit)
            prev_params = {**base_params, self.limit_param: limit, self.offset_param: prev_offset}
            prev_url = _build_url(request, prev_params)

        return {
            "count": total,
            "limit": limit,
            "offset": offset,
            "next": next_url,
            "previous": prev_url,
            "results": results,
        }


# ═══════════════════════════════════════════════════════════════════════════
#  CursorPagination
# ═══════════════════════════════════════════════════════════════════════════

class CursorPagination(BasePagination):
    """
    Cursor-based (keyset) pagination — efficient for very large datasets.

    Uses an opaque base64-encoded cursor pointing to the last item's
    ordering key, enabling constant-time page jumps regardless of dataset
    size (no OFFSET scan).

    Query params: ``?cursor=<opaque>&page_size=20``

    Response envelope::

        {
            "next": "http://host/items/?cursor=abc...",
            "previous": "http://host/items/?cursor=xyz...",
            "results": [...]
        }

    The ``ordering`` field determines the keyset column.
    """

    page_size: int = 20
    max_page_size: int = 1000
    cursor_param: str = "cursor"
    page_size_param: str = "page_size"
    ordering: str = "-id"  # Default ordering field

    def __init__(
        self,
        page_size: Optional[int] = None,
        ordering: Optional[str] = None,
    ):
        if page_size is not None:
            self.page_size = page_size
        if ordering is not None:
            self.ordering = ordering

    def _decode_cursor(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        try:
            decoded = base64.urlsafe_b64decode(raw + "==").decode("utf-8")
            return json.loads(decoded)
        except Exception:
            return None

    def _encode_cursor(self, data: Dict[str, Any]) -> str:
        raw = json.dumps(data, default=str).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def _get_page_size(self, request: Any) -> int:
        params = _get_current_params(request)
        try:
            size = int(params.get(self.page_size_param, self.page_size))
            return max(1, min(size, self.max_page_size))
        except (ValueError, TypeError):
            return self.page_size

    def paginate_list(
        self,
        data: List[Any],
        request: Any,
    ) -> Dict[str, Any]:
        params = _get_current_params(request)
        size = self._get_page_size(request)
        cursor_data = self._decode_cursor(params.get(self.cursor_param))

        desc = self.ordering.startswith("-")
        field_name = self.ordering.lstrip("-")

        # Sort data by the ordering field
        sorted_data = sorted(
            data,
            key=lambda x: _get_nested_value(x, field_name),
            reverse=desc,
        )

        # Apply cursor filter
        if cursor_data:
            cursor_value = cursor_data.get("v")
            cursor_direction = cursor_data.get("d", "next")

            if cursor_direction == "next":
                if desc:
                    sorted_data = [
                        item for item in sorted_data
                        if _compare_values(
                            _get_nested_value(item, field_name), cursor_value
                        ) < 0
                    ]
                else:
                    sorted_data = [
                        item for item in sorted_data
                        if _compare_values(
                            _get_nested_value(item, field_name), cursor_value
                        ) > 0
                    ]
            else:  # previous
                if desc:
                    sorted_data = [
                        item for item in sorted_data
                        if _compare_values(
                            _get_nested_value(item, field_name), cursor_value
                        ) > 0
                    ]
                else:
                    sorted_data = [
                        item for item in sorted_data
                        if _compare_values(
                            _get_nested_value(item, field_name), cursor_value
                        ) < 0
                    ]
                # Reverse so we paginate backwards correctly
                sorted_data = list(reversed(sorted_data))

        # Fetch one extra to detect has_next
        page = sorted_data[: size + 1]
        has_next = len(page) > size
        page = page[:size]

        base_params = _get_current_params(request)
        base_params.pop(self.cursor_param, None)

        next_url = None
        if has_next and page:
            last_val = _get_nested_value(page[-1], field_name)
            cursor = self._encode_cursor({"v": last_val, "d": "next"})
            next_params = {**base_params, self.cursor_param: cursor}
            next_url = _build_url(request, next_params)

        prev_url = None
        if cursor_data and page:
            first_val = _get_nested_value(page[0], field_name)
            cursor = self._encode_cursor({"v": first_val, "d": "prev"})
            prev_params = {**base_params, self.cursor_param: cursor}
            prev_url = _build_url(request, prev_params)

        return {
            "next": next_url,
            "previous": prev_url,
            "results": page,
        }

    async def paginate_queryset(
        self,
        queryset: Any,
        request: Any,
    ) -> Dict[str, Any]:
        """
        Cursor pagination on an ORM queryset.

        Uses WHERE + ORDER BY + LIMIT for true keyset pagination.
        """
        params = _get_current_params(request)
        size = self._get_page_size(request)
        cursor_data = self._decode_cursor(params.get(self.cursor_param))

        desc = self.ordering.startswith("-")
        field_name = self.ordering.lstrip("-")

        qs = queryset.order(self.ordering)

        if cursor_data:
            cursor_value = cursor_data.get("v")
            cursor_direction = cursor_data.get("d", "next")

            if cursor_direction == "next":
                if desc:
                    qs = qs.filter(**{f"{field_name}__lt": cursor_value})
                else:
                    qs = qs.filter(**{f"{field_name}__gt": cursor_value})
            else:
                if desc:
                    qs = qs.filter(**{f"{field_name}__gt": cursor_value})
                else:
                    qs = qs.filter(**{f"{field_name}__lt": cursor_value})
                # Reverse ordering for previous page
                reverse_order = field_name if desc else f"-{field_name}"
                qs = qs.order(reverse_order)

        try:
            items = await qs.limit(size + 1).all()
        except Exception:
            return await super().paginate_queryset(queryset, request)

        results = [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in items
        ]

        # For "prev" direction, re-reverse to restore original order
        if cursor_data and cursor_data.get("d") == "prev":
            results = list(reversed(results))

        has_next = len(results) > size
        results = results[:size]

        base_params = _get_current_params(request)
        base_params.pop(self.cursor_param, None)

        next_url = None
        if has_next and results:
            last_val = _get_nested_value(results[-1], field_name)
            cursor = self._encode_cursor({"v": last_val, "d": "next"})
            next_params = {**base_params, self.cursor_param: cursor}
            next_url = _build_url(request, next_params)

        prev_url = None
        if cursor_data and results:
            first_val = _get_nested_value(results[0], field_name)
            cursor = self._encode_cursor({"v": first_val, "d": "prev"})
            prev_params = {**base_params, self.cursor_param: cursor}
            prev_url = _build_url(request, prev_params)

        return {
            "next": next_url,
            "previous": prev_url,
            "results": results,
        }


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _get_nested_value(obj: Any, key: str) -> Any:
    """Get a value from a dict or object using dot notation."""
    parts = key.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _compare_values(a: Any, b: Any) -> int:
    """Compare two values, handling type differences."""
    if a is None and b is None:
        return 0
    if a is None:
        return -1
    if b is None:
        return 1
    try:
        # Try numeric comparison
        if isinstance(a, (int, float)) or isinstance(b, (int, float)):
            a_num = float(a) if not isinstance(a, (int, float)) else a
            b_num = float(b) if not isinstance(b, (int, float)) else b
            if a_num < b_num:
                return -1
            elif a_num > b_num:
                return 1
            return 0
        if a < b:
            return -1
        elif a > b:
            return 1
        return 0
    except TypeError:
        # String fallback
        sa, sb = str(a), str(b)
        if sa < sb:
            return -1
        elif sa > sb:
            return 1
        return 0
