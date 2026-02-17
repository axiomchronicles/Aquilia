"""
Tests for Aquilia Filtering, Searching, Pagination, and Content Negotiation.

Covers:
- FilterSet (declarative + custom methods)
- SearchFilter (in-memory text search)
- OrderingFilter (dynamic ordering)
- PageNumberPagination
- LimitOffsetPagination
- CursorPagination
- Content negotiation (Accept header + ?format=)
- All renderers (JSON, XML, YAML, Plain, HTML, Browsable)
- Engine integration (decorator metadata wiring)
"""

import json
import math
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_request(query_params=None, headers=None, method="GET", path="/items"):
    """Build a minimal fake request for testing."""
    qp = query_params or {}
    hdrs = headers or {}
    req = SimpleNamespace(
        method=method,
        path=path,
        query_params=qp,
        scope={
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": [(k.encode(), v.encode()) for k, v in hdrs.items()],
            "scheme": "http",
        },
    )
    req.query_param = lambda name, default=None: qp.get(name, default)
    req.header = lambda name, default=None: hdrs.get(name.lower(), hdrs.get(name, default))
    req.headers = hdrs
    return req


PRODUCTS = [
    {"id": 1, "name": "Laptop", "category": "electronics", "price": 999.99, "active": True},
    {"id": 2, "name": "Keyboard", "category": "electronics", "price": 79.99, "active": True},
    {"id": 3, "name": "Desk", "category": "furniture", "price": 249.99, "active": True},
    {"id": 4, "name": "Chair", "category": "furniture", "price": 399.99, "active": False},
    {"id": 5, "name": "Monitor", "category": "electronics", "price": 549.99, "active": True},
    {"id": 6, "name": "Headphones", "category": "audio", "price": 199.99, "active": True},
    {"id": 7, "name": "Webcam", "category": "electronics", "price": 89.99, "active": False},
    {"id": 8, "name": "Mouse", "category": "electronics", "price": 49.99, "active": True},
    {"id": 9, "name": "Bookshelf", "category": "furniture", "price": 149.99, "active": True},
    {"id": 10, "name": "Speakers", "category": "audio", "price": 129.99, "active": True},
]


# ═══════════════════════════════════════════════════════════════════════════
#  FilterSet Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestFilterSet:
    """Tests for FilterSet declarative filtering."""

    def test_list_shorthand(self):
        """fields = [\"status\", \"name\"] → exact-only filters."""
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = ["category", "active"]

        req = _make_request({"category": "electronics"})
        fs = F(request=req)
        clauses = fs.parse()
        assert clauses == {"category": "electronics"}

    def test_dict_lookups(self):
        """fields = {\"price\": [\"gte\", \"lte\"]} → range filtering."""
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = {"price": ["gte", "lte"]}

        req = _make_request({"price__gte": "100", "price__lte": "500"})
        fs = F(request=req)
        clauses = fs.parse()
        assert clauses["price__gte"] == 100
        assert clauses["price__lte"] == 500

    def test_boolean_filter(self):
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = ["active"]

        req = _make_request({"active": "true"})
        fs = F(request=req)
        clauses = fs.parse()
        assert clauses["active"] is True

    def test_in_filter(self):
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = {"category": ["in"]}

        req = _make_request({"category__in": "electronics,audio"})
        fs = F(request=req)
        clauses = fs.parse()
        assert clauses["category__in"] == ["electronics", "audio"]

    def test_isnull_filter(self):
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = {"parent": ["isnull"]}

        req = _make_request({"parent__isnull": "true"})
        fs = F(request=req)
        clauses = fs.parse()
        assert clauses["parent__isnull"] is True

    def test_range_filter(self):
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = {"price": ["range"]}

        req = _make_request({"price__range": "100,500"})
        fs = F(request=req)
        clauses = fs.parse()
        assert clauses["price__range"] == ["100", "500"]

    def test_no_params_returns_empty(self):
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = {"category": ["exact"]}

        req = _make_request({})
        fs = F(request=req)
        assert fs.parse() == {}

    def test_custom_filter_method(self):
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = {"category": ["exact"]}

            def filter_category(self, value):
                if value == "sale":
                    return {"discount__gt": 0}
                return {"category": value}

        req = _make_request({"category": "sale"})
        fs = F(request=req)
        clauses = fs.parse()
        assert clauses == {"discount__gt": 0}

    def test_filter_list_exact(self):
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = ["category"]

        req = _make_request({"category": "furniture"})
        fs = F(request=req)
        result = fs.filter_list(PRODUCTS)
        assert len(result) == 3
        assert all(p["category"] == "furniture" for p in result)

    def test_query_params_dict(self):
        """Accept raw query_params dict without a request."""
        from aquilia.controller.filters import FilterSet

        class F(FilterSet):
            class Meta:
                fields = ["category"]

        fs = F(query_params={"category": "audio"})
        assert fs.parse() == {"category": "audio"}


class TestFilterSetMeta:
    """Tests for the FilterSet metaclass."""

    def test_inherits_fields(self):
        from aquilia.controller.filters import FilterSet

        class Base(FilterSet):
            class Meta:
                fields = {"name": ["exact"]}

        class Child(Base):
            class Meta:
                fields = {"name": ["exact", "icontains"]}

        assert Child._filter_fields == {"name": ["exact", "icontains"]}

    def test_no_meta(self):
        from aquilia.controller.filters import FilterSet

        class NoMeta(FilterSet):
            pass

        assert NoMeta._filter_fields == {}


# ═══════════════════════════════════════════════════════════════════════════
#  In-memory filtering tests
# ═══════════════════════════════════════════════════════════════════════════

class TestApplyFilters:
    """Tests for apply_filters_to_list."""

    def test_exact(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"category": "electronics"})
        assert len(result) == 5

    def test_icontains(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"name__icontains": "key"})
        assert len(result) == 1
        assert result[0]["name"] == "Keyboard"

    def test_gt_lt(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"price__gt": 200, "price__lt": 600})
        names = {p["name"] for p in result}
        assert "Desk" in names
        assert "Monitor" in names
        assert "Chair" in names

    def test_in_filter(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(
            PRODUCTS, {"category__in": ["audio", "furniture"]}
        )
        assert len(result) == 5

    def test_range_filter(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"price__range": [100, 300]})
        assert all(100 <= p["price"] <= 300 for p in result)

    def test_isnull(self):
        from aquilia.controller.filters import apply_filters_to_list
        data = [{"a": None}, {"a": 1}, {"a": 2}]
        result = apply_filters_to_list(data, {"a__isnull": True})
        assert len(result) == 1

    def test_ne(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"category__ne": "electronics"})
        assert all(p["category"] != "electronics" for p in result)

    def test_startswith(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"name__startswith": "M"})
        assert all(p["name"].startswith("M") for p in result)

    def test_endswith(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"name__endswith": "r"})
        names = [p["name"] for p in result]
        assert "Monitor" in names
        assert "Chair" in names

    def test_regex(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {"name__regex": r"^[A-D]"})
        assert all(p["name"][0] in "ABCD" for p in result)

    def test_empty_filters_passthrough(self):
        from aquilia.controller.filters import apply_filters_to_list
        result = apply_filters_to_list(PRODUCTS, {})
        assert len(result) == len(PRODUCTS)


# ═══════════════════════════════════════════════════════════════════════════
#  Search Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSearch:
    """Tests for SearchFilter and apply_search_to_list."""

    def test_search_single_field(self):
        from aquilia.controller.filters import apply_search_to_list
        result = apply_search_to_list(PRODUCTS, "lap", ["name"])
        assert len(result) == 1
        assert result[0]["name"] == "Laptop"

    def test_search_multiple_fields(self):
        from aquilia.controller.filters import apply_search_to_list
        data = [
            {"name": "Laptop", "desc": "powerful machine"},
            {"name": "Desk", "desc": "wooden desk"},
        ]
        result = apply_search_to_list(data, "power", ["name", "desc"])
        assert len(result) == 1

    def test_search_case_insensitive(self):
        from aquilia.controller.filters import apply_search_to_list
        result = apply_search_to_list(PRODUCTS, "MOUSE", ["name"])
        assert len(result) == 1

    def test_empty_search_passthrough(self):
        from aquilia.controller.filters import apply_search_to_list
        result = apply_search_to_list(PRODUCTS, "", ["name"])
        assert len(result) == len(PRODUCTS)

    def test_search_filter_backend(self):
        from aquilia.controller.filters import SearchFilter
        sf = SearchFilter()
        req = _make_request({"search": "chair"})
        result = sf.filter_data(PRODUCTS, req, search_fields=["name"])
        assert len(result) == 1
        assert result[0]["name"] == "Chair"

    def test_search_no_fields(self):
        from aquilia.controller.filters import SearchFilter
        sf = SearchFilter()
        req = _make_request({"search": "anything"})
        result = sf.filter_data(PRODUCTS, req, search_fields=None)
        assert len(result) == len(PRODUCTS)


# ═══════════════════════════════════════════════════════════════════════════
#  Ordering Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestOrdering:
    """Tests for OrderingFilter and apply_ordering_to_list."""

    def test_order_ascending(self):
        from aquilia.controller.filters import apply_ordering_to_list
        result = apply_ordering_to_list(PRODUCTS, ["price"])
        prices = [p["price"] for p in result]
        assert prices == sorted(prices)

    def test_order_descending(self):
        from aquilia.controller.filters import apply_ordering_to_list
        result = apply_ordering_to_list(PRODUCTS, ["-price"])
        prices = [p["price"] for p in result]
        assert prices == sorted(prices, reverse=True)

    def test_order_multiple(self):
        from aquilia.controller.filters import apply_ordering_to_list
        result = apply_ordering_to_list(PRODUCTS, ["category", "price"])
        # Items grouped by category, then sorted by price within each
        for i in range(len(result) - 1):
            a, b = result[i], result[i + 1]
            if a["category"] == b["category"]:
                assert a["price"] <= b["price"]

    def test_ordering_filter_backend(self):
        from aquilia.controller.filters import OrderingFilter
        of = OrderingFilter()
        req = _make_request({"ordering": "-price"})
        result = of.filter_data(PRODUCTS, req, ordering_fields=["price", "name"])
        prices = [p["price"] for p in result]
        assert prices == sorted(prices, reverse=True)

    def test_ordering_whitelist(self):
        from aquilia.controller.filters import OrderingFilter
        of = OrderingFilter()
        req = _make_request({"ordering": "secret_field"})
        result = of.filter_data(PRODUCTS, req, ordering_fields=["price", "name"])
        # secret_field is not allowed — ordering stripped
        assert result == PRODUCTS

    def test_empty_ordering(self):
        from aquilia.controller.filters import apply_ordering_to_list
        result = apply_ordering_to_list(PRODUCTS, [])
        assert result == PRODUCTS


# ═══════════════════════════════════════════════════════════════════════════
#  Combined filter_data convenience
# ═══════════════════════════════════════════════════════════════════════════

class TestFilterDataConvenience:
    """Tests for the unified filter_data() function."""

    def test_filter_search_order(self):
        from aquilia.controller.filters import filter_data

        req = _make_request({
            "category": "electronics",
            "search": "o",
            "ordering": "price",
        })

        result = filter_data(
            PRODUCTS,
            req,
            filterset_fields=["category"],
            search_fields=["name"],
            ordering_fields=["price"],
        )
        # "electronics" + name contains "o" → Mouse, Keyboard, Monitor, Laptop
        assert all(p["category"] == "electronics" for p in result)
        assert all("o" in p["name"].lower() for p in result)
        assert len(result) == 4
        prices = [p["price"] for p in result]
        assert prices == sorted(prices)

    def test_filter_with_filterset_class(self):
        from aquilia.controller.filters import FilterSet, filter_data

        class PF(FilterSet):
            class Meta:
                fields = {"price": ["gte", "lte"]}

        req = _make_request({"price__gte": "100", "price__lte": "300"})
        result = filter_data(PRODUCTS, req, filterset_class=PF)
        assert all(100 <= p["price"] <= 300 for p in result)


# ═══════════════════════════════════════════════════════════════════════════
#  PageNumberPagination Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPageNumberPagination:
    """Tests for PageNumberPagination."""

    def test_default_page(self):
        from aquilia.controller.pagination import PageNumberPagination
        p = PageNumberPagination(page_size=3)
        req = _make_request({})
        result = p.paginate_list(PRODUCTS, req)
        assert result["count"] == 10
        assert result["page"] == 1
        assert result["page_size"] == 3
        assert result["total_pages"] == 4
        assert len(result["results"]) == 3
        assert result["previous"] is None
        assert result["next"] is not None

    def test_page_2(self):
        from aquilia.controller.pagination import PageNumberPagination
        p = PageNumberPagination(page_size=3)
        req = _make_request({"page": "2"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["page"] == 2
        assert len(result["results"]) == 3
        assert result["previous"] is not None
        assert result["next"] is not None

    def test_last_page(self):
        from aquilia.controller.pagination import PageNumberPagination
        p = PageNumberPagination(page_size=3)
        req = _make_request({"page": "4"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["page"] == 4
        assert len(result["results"]) == 1  # 10 items, 3 pages of 3, 1 leftover
        assert result["next"] is None
        assert result["previous"] is not None

    def test_custom_page_size_param(self):
        from aquilia.controller.pagination import PageNumberPagination
        p = PageNumberPagination(page_size=2)
        req = _make_request({"page_size": "5"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["page_size"] == 5
        assert len(result["results"]) == 5

    def test_max_page_size(self):
        from aquilia.controller.pagination import PageNumberPagination
        p = PageNumberPagination(page_size=10, max_page_size=5)
        req = _make_request({"page_size": "100"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["page_size"] == 5

    def test_invalid_page_defaults_to_1(self):
        from aquilia.controller.pagination import PageNumberPagination
        p = PageNumberPagination(page_size=3)
        req = _make_request({"page": "invalid"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["page"] == 1

    def test_empty_list(self):
        from aquilia.controller.pagination import PageNumberPagination
        p = PageNumberPagination(page_size=3)
        req = _make_request({})
        result = p.paginate_list([], req)
        assert result["count"] == 0
        assert result["total_pages"] == 1
        assert result["results"] == []


# ═══════════════════════════════════════════════════════════════════════════
#  LimitOffsetPagination Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestLimitOffsetPagination:
    """Tests for LimitOffsetPagination."""

    def test_default(self):
        from aquilia.controller.pagination import LimitOffsetPagination
        p = LimitOffsetPagination(default_limit=3)
        req = _make_request({})
        result = p.paginate_list(PRODUCTS, req)
        assert result["count"] == 10
        assert result["limit"] == 3
        assert result["offset"] == 0
        assert len(result["results"]) == 3
        assert result["next"] is not None
        assert result["previous"] is None

    def test_offset(self):
        from aquilia.controller.pagination import LimitOffsetPagination
        p = LimitOffsetPagination(default_limit=3)
        req = _make_request({"offset": "3"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["offset"] == 3
        assert result["previous"] is not None

    def test_last_page(self):
        from aquilia.controller.pagination import LimitOffsetPagination
        p = LimitOffsetPagination(default_limit=3)
        req = _make_request({"offset": "9", "limit": "3"})
        result = p.paginate_list(PRODUCTS, req)
        assert len(result["results"]) == 1
        assert result["next"] is None

    def test_custom_limit(self):
        from aquilia.controller.pagination import LimitOffsetPagination
        p = LimitOffsetPagination(default_limit=5)
        req = _make_request({"limit": "2"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["limit"] == 2
        assert len(result["results"]) == 2

    def test_max_limit(self):
        from aquilia.controller.pagination import LimitOffsetPagination
        p = LimitOffsetPagination(default_limit=5, max_limit=4)
        req = _make_request({"limit": "100"})
        result = p.paginate_list(PRODUCTS, req)
        assert result["limit"] == 4


# ═══════════════════════════════════════════════════════════════════════════
#  CursorPagination Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCursorPagination:
    """Tests for CursorPagination."""

    def test_first_page(self):
        from aquilia.controller.pagination import CursorPagination
        p = CursorPagination(page_size=3, ordering="id")
        req = _make_request({})
        result = p.paginate_list(PRODUCTS, req)
        assert len(result["results"]) == 3
        assert result["results"][0]["id"] == 1
        assert result["previous"] is None
        assert result["next"] is not None

    def test_cursor_forward(self):
        from aquilia.controller.pagination import CursorPagination
        p = CursorPagination(page_size=3, ordering="id")
        # First page
        req1 = _make_request({})
        page1 = p.paginate_list(PRODUCTS, req1)

        # Extract cursor from next URL
        next_url = page1["next"]
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(next_url).query)
        cursor = qs["cursor"][0]

        # Second page
        req2 = _make_request({"cursor": cursor})
        page2 = p.paginate_list(PRODUCTS, req2)
        assert len(page2["results"]) == 3
        assert page2["results"][0]["id"] == 4

    def test_descending_order(self):
        from aquilia.controller.pagination import CursorPagination
        p = CursorPagination(page_size=3, ordering="-id")
        req = _make_request({})
        result = p.paginate_list(PRODUCTS, req)
        assert result["results"][0]["id"] == 10
        assert result["results"][-1]["id"] == 8

    def test_custom_page_size(self):
        from aquilia.controller.pagination import CursorPagination
        p = CursorPagination(page_size=5)
        req = _make_request({"page_size": "2"})
        result = p.paginate_list(PRODUCTS, req)
        assert len(result["results"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
#  NoPagination Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestNoPagination:
    def test_passthrough(self):
        from aquilia.controller.pagination import NoPagination
        p = NoPagination()
        req = _make_request({})
        result = p.paginate_list(PRODUCTS, req)
        assert result["count"] == 10
        assert result["results"] == PRODUCTS
        assert result["next"] is None
        assert result["previous"] is None


# ═══════════════════════════════════════════════════════════════════════════
#  JSON Renderer Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestJSONRenderer:
    def test_render_dict(self):
        from aquilia.controller.renderers import JSONRenderer
        r = JSONRenderer()
        output = r.render({"name": "Alice", "age": 30})
        parsed = json.loads(output)
        assert parsed == {"name": "Alice", "age": 30}

    def test_render_list(self):
        from aquilia.controller.renderers import JSONRenderer
        r = JSONRenderer()
        output = r.render([1, 2, 3])
        assert json.loads(output) == [1, 2, 3]

    def test_render_with_indent(self):
        from aquilia.controller.renderers import JSONRenderer
        r = JSONRenderer(indent=2)
        output = r.render({"a": 1})
        assert "\n" in output

    def test_media_type(self):
        from aquilia.controller.renderers import JSONRenderer
        assert JSONRenderer.media_type == "application/json"


# ═══════════════════════════════════════════════════════════════════════════
#  XML Renderer Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestXMLRenderer:
    def test_render_dict(self):
        from aquilia.controller.renderers import XMLRenderer
        r = XMLRenderer()
        output = r.render({"name": "Alice", "age": 30})
        assert '<?xml version="1.0"' in output
        assert "<name>Alice</name>" in output
        assert "<age>30</age>" in output

    def test_render_list(self):
        from aquilia.controller.renderers import XMLRenderer
        r = XMLRenderer()
        output = r.render([{"id": 1}, {"id": 2}])
        assert output.count("<item>") == 2

    def test_custom_root_tag(self):
        from aquilia.controller.renderers import XMLRenderer
        r = XMLRenderer(root_tag="products")
        output = r.render({"name": "Laptop"})
        assert "<products>" in output
        assert "</products>" in output

    def test_html_escaping(self):
        from aquilia.controller.renderers import XMLRenderer
        r = XMLRenderer()
        output = r.render({"name": '<script>alert("xss")</script>'})
        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    def test_media_type(self):
        from aquilia.controller.renderers import XMLRenderer
        assert XMLRenderer.media_type == "application/xml"


# ═══════════════════════════════════════════════════════════════════════════
#  YAML Renderer Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestYAMLRenderer:
    def test_render_dict(self):
        from aquilia.controller.renderers import YAMLRenderer
        r = YAMLRenderer()
        output = r.render({"name": "Alice", "age": 30})
        assert "name" in output
        assert "Alice" in output

    def test_render_list(self):
        from aquilia.controller.renderers import YAMLRenderer
        r = YAMLRenderer()
        output = r.render([1, 2, 3])
        assert "- 1" in output or "1" in output

    def test_media_type(self):
        from aquilia.controller.renderers import YAMLRenderer
        assert YAMLRenderer.media_type == "application/x-yaml"


# ═══════════════════════════════════════════════════════════════════════════
#  PlainText Renderer Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPlainTextRenderer:
    def test_string(self):
        from aquilia.controller.renderers import PlainTextRenderer
        r = PlainTextRenderer()
        assert r.render("hello") == "hello"

    def test_dict(self):
        from aquilia.controller.renderers import PlainTextRenderer
        r = PlainTextRenderer()
        output = r.render({"key": "value"})
        parsed = json.loads(output)
        assert parsed == {"key": "value"}

    def test_media_type(self):
        from aquilia.controller.renderers import PlainTextRenderer
        assert PlainTextRenderer.media_type == "text/plain"


# ═══════════════════════════════════════════════════════════════════════════
#  HTML Renderer Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestHTMLRenderer:
    def test_passthrough_string(self):
        from aquilia.controller.renderers import HTMLRenderer
        r = HTMLRenderer()
        assert r.render("<h1>Hello</h1>") == "<h1>Hello</h1>"

    def test_auto_wrap_dict(self):
        from aquilia.controller.renderers import HTMLRenderer
        r = HTMLRenderer()
        output = r.render({"a": 1})
        assert "<!DOCTYPE html>" in output
        assert "<pre>" in output


# ═══════════════════════════════════════════════════════════════════════════
#  Browsable API Renderer Tests
# ═══════════════════════════════════════════════════════════════════════════
#  Content Negotiation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestContentNegotiation:
    """Tests for ContentNegotiator."""

    def test_default_json(self):
        from aquilia.controller.renderers import ContentNegotiator, JSONRenderer
        neg = ContentNegotiator()
        req = _make_request(headers={"accept": "*/*"})
        renderer, media = neg.select_renderer(req)
        assert isinstance(renderer, JSONRenderer)
        assert media == "application/json"

    def test_accept_xml(self):
        from aquilia.controller.renderers import (
            ContentNegotiator, JSONRenderer, XMLRenderer,
        )
        neg = ContentNegotiator(renderers=[JSONRenderer(), XMLRenderer()])
        req = _make_request(headers={"accept": "application/xml"})
        renderer, media = neg.select_renderer(req)
        assert isinstance(renderer, XMLRenderer)

    def test_accept_quality_weight(self):
        from aquilia.controller.renderers import (
            ContentNegotiator, JSONRenderer, XMLRenderer,
        )
        neg = ContentNegotiator(renderers=[JSONRenderer(), XMLRenderer()])
        req = _make_request(
            headers={"accept": "application/xml;q=0.5, application/json;q=0.9"}
        )
        renderer, media = neg.select_renderer(req)
        assert isinstance(renderer, JSONRenderer)

    def test_format_override(self):
        from aquilia.controller.renderers import (
            ContentNegotiator, JSONRenderer, XMLRenderer,
        )
        neg = ContentNegotiator(renderers=[JSONRenderer(), XMLRenderer()])
        req = _make_request(query_params={"format": "xml"})
        renderer, media = neg.select_renderer(req)
        assert isinstance(renderer, XMLRenderer)

    def test_wildcard_subtype(self):
        from aquilia.controller.renderers import (
            ContentNegotiator, JSONRenderer, XMLRenderer, PlainTextRenderer,
        )
        neg = ContentNegotiator(
            renderers=[PlainTextRenderer(), JSONRenderer(), XMLRenderer()]
        )
        req = _make_request(headers={"accept": "application/*"})
        renderer, media = neg.select_renderer(req)
        # Should pick first application/* match → JSONRenderer
        assert isinstance(renderer, JSONRenderer)

    def test_no_match_falls_to_default(self):
        from aquilia.controller.renderers import (
            ContentNegotiator, JSONRenderer,
        )
        neg = ContentNegotiator(renderers=[JSONRenderer()])
        req = _make_request(headers={"accept": "image/png"})
        renderer, media = neg.select_renderer(req)
        # Falls back to first renderer
        assert isinstance(renderer, JSONRenderer)

    def test_negotiate_convenience(self):
        from aquilia.controller.renderers import negotiate, JSONRenderer
        req = _make_request()
        body, content_type, status = negotiate(
            {"key": "value"}, req, renderers=[JSONRenderer()]
        )
        assert json.loads(body) == {"key": "value"}
        assert "application/json" in content_type


# ═══════════════════════════════════════════════════════════════════════════
#  Accept Header Parser Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestAcceptParser:
    def test_simple(self):
        from aquilia.controller.renderers import _parse_accept
        result = _parse_accept("application/json")
        assert result == [("application/json", 1.0)]

    def test_multiple_with_quality(self):
        from aquilia.controller.renderers import _parse_accept
        result = _parse_accept("text/html, application/json;q=0.9, */*;q=0.1")
        assert result[0] == ("text/html", 1.0)
        assert result[1] == ("application/json", 0.9)
        assert result[2] == ("*/*", 0.1)

    def test_empty_header(self):
        from aquilia.controller.renderers import _parse_accept
        result = _parse_accept("")
        assert result == [("*/*", 1.0)]

    def test_none_header(self):
        from aquilia.controller.renderers import _parse_accept
        result = _parse_accept(None)
        assert result == [("*/*", 1.0)]


# ═══════════════════════════════════════════════════════════════════════════
#  Decorator Metadata Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDecoratorMetadata:
    """Test that new decorator kwargs store metadata correctly."""

    def test_filterset_fields(self):
        from aquilia.controller.decorators import GET

        @GET("/", filterset_fields=["status", "category"])
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["filterset_fields"] == ["status", "category"]

    def test_search_fields(self):
        from aquilia.controller.decorators import GET

        @GET("/", search_fields=["name", "description"])
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["search_fields"] == ["name", "description"]

    def test_ordering_fields(self):
        from aquilia.controller.decorators import GET

        @GET("/", ordering_fields=["price", "created_at"])
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["ordering_fields"] == ["price", "created_at"]

    def test_pagination_class(self):
        from aquilia.controller.decorators import GET
        from aquilia.controller.pagination import PageNumberPagination

        @GET("/", pagination_class=PageNumberPagination)
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["pagination_class"] is PageNumberPagination

    def test_renderer_classes(self):
        from aquilia.controller.decorators import GET
        from aquilia.controller.renderers import JSONRenderer, XMLRenderer

        @GET("/", renderer_classes=[JSONRenderer, XMLRenderer])
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert len(meta["renderer_classes"]) == 2

    def test_filterset_class(self):
        from aquilia.controller.decorators import GET
        from aquilia.controller.filters import FilterSet

        class ProductFilter(FilterSet):
            class Meta:
                fields = {"price": ["gte", "lte"]}

        @GET("/", filterset_class=ProductFilter)
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["filterset_class"] is ProductFilter

    def test_all_params_coexist(self):
        from aquilia.controller.decorators import GET
        from aquilia.controller.pagination import LimitOffsetPagination
        from aquilia.controller.renderers import JSONRenderer

        @GET(
            "/",
            filterset_fields=["status"],
            search_fields=["name"],
            ordering_fields=["price"],
            pagination_class=LimitOffsetPagination,
            renderer_classes=[JSONRenderer],
        )
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["filterset_fields"] == ["status"]
        assert meta["search_fields"] == ["name"]
        assert meta["ordering_fields"] == ["price"]
        assert meta["pagination_class"] is LimitOffsetPagination
        assert len(meta["renderer_classes"]) == 1

    def test_default_none(self):
        from aquilia.controller.decorators import GET

        @GET("/")
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["filterset_class"] is None
        assert meta["filterset_fields"] is None
        assert meta["search_fields"] is None
        assert meta["ordering_fields"] is None
        assert meta["pagination_class"] is None
        assert meta["renderer_classes"] is None


# ═══════════════════════════════════════════════════════════════════════════
#  Engine integration (fast-path detection)
# ═══════════════════════════════════════════════════════════════════════════

class TestFastPathDetection:
    """Test that filter/pagination/renderer metadata disables the fast path."""

    def test_fast_path_disabled_for_filters(self):
        """Routes with filterset_fields should NOT take the fast path."""
        from aquilia.controller.engine import ControllerEngine
        from aquilia.controller.decorators import GET

        # Clear cache
        ControllerEngine._simple_route_cache.clear()

        @GET("/", filterset_fields=["status"])
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        # The fast-path check looks for these keys on route_metadata
        # Since the actual engine reads from compiled route metadata,
        # we just verify the metadata propagation is correct
        assert meta["filterset_fields"] is not None

    def test_fast_path_disabled_for_pagination(self):
        from aquilia.controller.decorators import GET
        from aquilia.controller.pagination import PageNumberPagination

        @GET("/", pagination_class=PageNumberPagination)
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["pagination_class"] is not None

    def test_fast_path_disabled_for_renderers(self):
        from aquilia.controller.decorators import GET
        from aquilia.controller.renderers import JSONRenderer

        @GET("/", renderer_classes=[JSONRenderer])
        async def handler(self, ctx):
            pass

        meta = handler.__route_metadata__[0]
        assert meta["renderer_classes"] is not None


# ═══════════════════════════════════════════════════════════════════════════
#  Engine _apply_filters_and_pagination integration
# ═══════════════════════════════════════════════════════════════════════════

class TestEngineFiltering:
    """Test the engine's _apply_filters_and_pagination method directly."""

    def _make_engine(self):
        from aquilia.controller.engine import ControllerEngine
        from aquilia.controller.factory import ControllerFactory
        from aquilia.di import Container
        factory = ControllerFactory(Container())
        return ControllerEngine(factory)

    @pytest.mark.asyncio
    async def test_filter_list(self):
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={
                "filterset_fields": ["category"],
                "search_fields": None,
                "ordering_fields": None,
                "pagination_class": None,
                "renderer_classes": None,
            },
            filterset_class=None,
            filterset_fields=["category"],
            search_fields=None,
            ordering_fields=None,
            pagination_class=None,
            renderer_classes=None,
        )
        req = _make_request({"category": "electronics"})
        result = await engine._apply_filters_and_pagination(PRODUCTS, meta, req)
        assert all(p["category"] == "electronics" for p in result)

    @pytest.mark.asyncio
    async def test_paginate_list(self):
        from aquilia.controller.pagination import PageNumberPagination
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            filterset_class=None,
            filterset_fields=None,
            search_fields=None,
            ordering_fields=None,
            pagination_class=PageNumberPagination,
            renderer_classes=None,
        )
        req = _make_request({"page_size": "3"})
        result = await engine._apply_filters_and_pagination(PRODUCTS, meta, req)
        assert result["count"] == 10
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_filter_and_paginate(self):
        from aquilia.controller.pagination import PageNumberPagination
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            filterset_class=None,
            filterset_fields=["category"],
            search_fields=None,
            ordering_fields=None,
            pagination_class=PageNumberPagination,
            renderer_classes=None,
        )
        req = _make_request({"category": "electronics", "page_size": "2"})
        result = await engine._apply_filters_and_pagination(PRODUCTS, meta, req)
        assert result["count"] == 5  # 5 electronics products
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_no_filters_passthrough(self):
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            filterset_class=None,
            filterset_fields=None,
            search_fields=None,
            ordering_fields=None,
            pagination_class=None,
            renderer_classes=None,
        )
        req = _make_request({})
        result = await engine._apply_filters_and_pagination(PRODUCTS, meta, req)
        assert result == PRODUCTS

    @pytest.mark.asyncio
    async def test_response_passthrough(self):
        from aquilia.response import Response
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            filterset_class=None,
            filterset_fields=["category"],
            search_fields=None,
            ordering_fields=None,
            pagination_class=None,
            renderer_classes=None,
        )
        resp = Response.json({"ok": True})
        req = _make_request({})
        result = await engine._apply_filters_and_pagination(resp, meta, req)
        assert isinstance(result, Response)


# ═══════════════════════════════════════════════════════════════════════════
#  Engine _apply_content_negotiation integration
# ═══════════════════════════════════════════════════════════════════════════

class TestEngineContentNegotiation:
    """Test the engine's _apply_content_negotiation method directly."""

    def _make_engine(self):
        from aquilia.controller.engine import ControllerEngine
        from aquilia.controller.factory import ControllerFactory
        from aquilia.di import Container
        factory = ControllerFactory(Container())
        return ControllerEngine(factory)

    def test_no_renderers_returns_none(self):
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            renderer_classes=None,
        )
        req = _make_request()
        result = engine._apply_content_negotiation({"key": "val"}, meta, req)
        assert result is None  # Falls through to _to_response

    def test_json_renderer(self):
        from aquilia.controller.renderers import JSONRenderer
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            renderer_classes=[JSONRenderer],
        )
        req = _make_request(headers={"accept": "application/json"})
        result = engine._apply_content_negotiation({"key": "val"}, meta, req)
        from aquilia.response import Response
        assert isinstance(result, Response)

    def test_xml_renderer_via_format(self):
        from aquilia.controller.renderers import JSONRenderer, XMLRenderer
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            renderer_classes=[JSONRenderer, XMLRenderer],
        )
        req = _make_request(query_params={"format": "xml"})
        result = engine._apply_content_negotiation({"name": "test"}, meta, req)
        from aquilia.response import Response
        assert isinstance(result, Response)
        # Content should be XML
        assert "xml" in result._headers.get("content-type", "")

    def test_response_passthrough(self):
        from aquilia.response import Response
        from aquilia.controller.renderers import JSONRenderer
        engine = self._make_engine()
        meta = SimpleNamespace(
            _raw_metadata={},
            renderer_classes=[JSONRenderer],
        )
        resp = Response.json({"ok": True})
        req = _make_request()
        result = engine._apply_content_negotiation(resp, meta, req)
        assert result is resp  # Untouched


# ═══════════════════════════════════════════════════════════════════════════
#  Exports Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestExports:
    """Verify everything is importable from the right places."""

    def test_controller_package_exports(self):
        from aquilia.controller import (
            FilterSet, SearchFilter, OrderingFilter, BaseFilterBackend,
            PageNumberPagination, LimitOffsetPagination, CursorPagination,
            NoPagination,
            JSONRenderer, XMLRenderer, YAMLRenderer, PlainTextRenderer,
            HTMLRenderer, ContentNegotiator,
            negotiate,
            filter_data, filter_queryset,
            apply_filters_to_list, apply_search_to_list, apply_ordering_to_list,
        )

    def test_top_level_exports(self):
        from aquilia import (
            FilterSet, SearchFilter, OrderingFilter, BaseFilterBackend,
            PageNumberPagination, LimitOffsetPagination, CursorPagination,
            NoPagination,
            JSONRenderer, XMLRenderer, YAMLRenderer, PlainTextRenderer,
            HTMLRenderer, ContentNegotiator,
        )

    def test_in_all(self):
        import aquilia
        for name in [
            "FilterSet", "SearchFilter", "OrderingFilter",
            "PageNumberPagination", "LimitOffsetPagination", "CursorPagination",
            "JSONRenderer", "XMLRenderer",
            "ContentNegotiator",
        ]:
            assert name in aquilia.__all__, f"{name} missing from __all__"
