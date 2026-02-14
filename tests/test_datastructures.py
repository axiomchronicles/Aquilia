"""
Test 1: Core Data Structures (_datastructures.py)

Tests MultiDict, Headers, URL, ParsedContentType, Range, and utility functions.
"""

import pytest
from aquilia._datastructures import (
    MultiDict, Headers, URL, ParsedContentType, Range,
    parse_authorization_header, parse_date_header,
)


# ============================================================================
# MultiDict
# ============================================================================

class TestMultiDict:
    """MultiDict - multi-value dictionary for query params and form data."""

    def test_init_empty(self):
        md = MultiDict()
        assert len(md) == 0

    def test_init_from_list(self):
        md = MultiDict([("a", "1"), ("b", "2"), ("a", "3")])
        assert md.get("a") == "1"
        assert md.get_all("a") == ["1", "3"]
        assert md.get("b") == "2"

    def test_init_from_dict(self):
        md = MultiDict({"x": "10", "y": ["20", "30"]})
        assert md.get("x") == "10"
        assert md.get_all("y") == ["20", "30"]

    def test_add(self):
        md = MultiDict()
        md.add("k", "v1")
        md.add("k", "v2")
        assert md.get_all("k") == ["v1", "v2"]
        assert md.get("k") == "v1"

    def test_setitem_replaces(self):
        md = MultiDict([("a", "1"), ("a", "2")])
        md["a"] = "replaced"
        assert md.get("a") == "replaced"
        assert md.get_all("a") == ["replaced"]

    def test_delitem(self):
        md = MultiDict([("a", "1")])
        del md["a"]
        assert len(md) == 0
        with pytest.raises(KeyError):
            del md["nonexistent"]

    def test_get_default(self):
        md = MultiDict()
        assert md.get("missing") is None
        assert md.get("missing", "fallback") == "fallback"

    def test_items_list(self):
        md = MultiDict([("a", "1"), ("b", "2"), ("a", "3")])
        items = md.items_list()
        assert ("a", "1") in items
        assert ("a", "3") in items
        assert ("b", "2") in items
        assert len(items) == 3

    def test_to_dict_single(self):
        md = MultiDict([("a", "1"), ("a", "2"), ("b", "3")])
        d = md.to_dict(multi=False)
        assert d == {"a": "1", "b": "3"}

    def test_to_dict_multi(self):
        md = MultiDict([("a", "1"), ("a", "2")])
        d = md.to_dict(multi=True)
        assert d == {"a": ["1", "2"]}

    def test_len(self):
        md = MultiDict([("a", "1"), ("a", "2"), ("b", "3")])
        assert len(md) == 2  # 2 unique keys

    def test_iter(self):
        md = MultiDict([("x", "1"), ("y", "2")])
        assert sorted(list(md)) == ["x", "y"]

    def test_repr(self):
        md = MultiDict([("a", "1")])
        assert "MultiDict" in repr(md)


# ============================================================================
# Headers
# ============================================================================

class TestHeaders:
    """Headers - case-insensitive header access."""

    def test_get_case_insensitive(self):
        h = Headers(raw=[(b"Content-Type", b"text/html"), (b"X-Custom", b"val")])
        assert h.get("content-type") == "text/html"
        assert h.get("CONTENT-TYPE") == "text/html"
        assert h.get("x-custom") == "val"

    def test_get_default(self):
        h = Headers(raw=[])
        assert h.get("missing") is None
        assert h.get("missing", "default") == "default"

    def test_get_all(self):
        h = Headers(raw=[(b"Set-Cookie", b"a=1"), (b"Set-Cookie", b"b=2")])
        all_vals = h.get_all("set-cookie")
        assert len(all_vals) == 2
        assert "a=1" in all_vals
        assert "b=2" in all_vals

    def test_has(self):
        h = Headers(raw=[(b"Authorization", b"Bearer xxx")])
        assert h.has("authorization") is True
        assert h.has("missing") is False

    def test_contains_dunder(self):
        h = Headers(raw=[(b"Host", b"example.com")])
        assert "host" in h
        assert "Host" in h
        assert "missing" not in h

    def test_getitem(self):
        h = Headers(raw=[(b"Host", b"example.com")])
        assert h["host"] == "example.com"
        with pytest.raises(KeyError):
            h["missing"]

    def test_items_keys_values(self):
        h = Headers(raw=[(b"A", b"1"), (b"B", b"2")])
        items = list(h.items())
        assert ("A", "1") in items
        assert ("B", "2") in items
        keys = list(h.keys())
        assert "A" in keys
        assert "B" in keys
        values = list(h.values())
        assert "1" in values
        assert "2" in values


# ============================================================================
# URL
# ============================================================================

class TestURL:
    """URL - parsed URL representation."""

    def test_parse_full(self):
        url = URL.parse("https://user:pass@example.com:8443/path?q=1#frag")
        assert url.scheme == "https"
        assert url.host == "example.com"
        assert url.port == 8443
        assert url.path == "/path"
        assert url.query == "q=1"
        assert url.fragment == "frag"
        assert url.username == "user"
        assert url.password == "pass"

    def test_parse_simple(self):
        url = URL.parse("http://localhost/api")
        assert url.scheme == "http"
        assert url.host == "localhost"
        assert url.path == "/api"

    def test_str_roundtrip(self):
        original = "https://example.com:8443/path?q=1"
        url = URL.parse(original)
        assert str(url) == original

    def test_netloc_standard_port(self):
        url = URL(scheme="http", host="example.com", port=80, path="/")
        assert url.netloc == "example.com"

    def test_netloc_non_standard_port(self):
        url = URL(scheme="http", host="example.com", port=8080, path="/")
        assert url.netloc == "example.com:8080"

    def test_replace(self):
        url = URL(scheme="http", host="a.com", path="/old")
        new_url = url.replace(path="/new", scheme="https")
        assert new_url.path == "/new"
        assert new_url.scheme == "https"
        assert new_url.host == "a.com"  # Unchanged

    def test_with_query(self):
        url = URL(scheme="http", host="a.com", path="/")
        new_url = url.with_query(page="2", sort="name")
        assert "page=2" in new_url.query
        assert "sort=name" in new_url.query


# ============================================================================
# ParsedContentType
# ============================================================================

class TestParsedContentType:
    """ParsedContentType - Content-Type header parsing."""

    def test_parse_simple(self):
        ct = ParsedContentType.parse("application/json")
        assert ct is not None
        assert ct.media_type == "application/json"
        assert ct.charset == "utf-8"  # Default

    def test_parse_with_charset(self):
        ct = ParsedContentType.parse("text/html; charset=iso-8859-1")
        assert ct.media_type == "text/html"
        assert ct.charset == "iso-8859-1"

    def test_parse_multipart_boundary(self):
        ct = ParsedContentType.parse("multipart/form-data; boundary=abc123")
        assert ct.media_type == "multipart/form-data"
        assert ct.boundary == "abc123"

    def test_parse_none(self):
        assert ParsedContentType.parse(None) is None

    def test_parse_empty(self):
        assert ParsedContentType.parse("") is None


# ============================================================================
# Range
# ============================================================================

class TestRange:
    """Range - HTTP Range header parsing."""

    def test_parse_single(self):
        r = Range.parse("bytes=0-499")
        assert r is not None
        assert r.unit == "bytes"
        assert r.ranges == [(0, 499)]

    def test_parse_suffix(self):
        r = Range.parse("bytes=-500")
        assert r.ranges == [(None, 500)]

    def test_parse_open_end(self):
        r = Range.parse("bytes=500-")
        assert r.ranges == [(500, None)]

    def test_parse_multi(self):
        r = Range.parse("bytes=0-99,200-299")
        assert len(r.ranges) == 2
        assert r.ranges[0] == (0, 99)
        assert r.ranges[1] == (200, 299)

    def test_parse_none(self):
        assert Range.parse(None) is None

    def test_str_roundtrip(self):
        r = Range.parse("bytes=0-499")
        assert str(r) == "bytes=0-499"


# ============================================================================
# Utility Functions
# ============================================================================

class TestUtilityFunctions:
    """parse_authorization_header and parse_date_header."""

    def test_parse_auth_bearer(self):
        result = parse_authorization_header("Bearer token123")
        assert result == ("Bearer", "token123")

    def test_parse_auth_basic(self):
        result = parse_authorization_header("Basic dXNlcjpwYXNz")
        assert result == ("Basic", "dXNlcjpwYXNz")

    def test_parse_auth_none(self):
        assert parse_authorization_header(None) is None

    def test_parse_auth_invalid(self):
        assert parse_authorization_header("JustAToken") is None

    def test_parse_date_header_valid(self):
        result = parse_date_header("Sat, 01 Jan 2000 00:00:00 GMT")
        assert result is not None

    def test_parse_date_header_none(self):
        assert parse_date_header(None) is None

    def test_parse_date_header_invalid(self):
        assert parse_date_header("not-a-date") is None
