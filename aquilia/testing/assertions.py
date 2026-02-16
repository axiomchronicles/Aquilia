"""
Aquilia Testing - Custom Assertion Helpers.

Provides rich, descriptive assertions tailored to Aquilia's response
model, fault system, DI container, config, cache, effects, and mail.
"""

from __future__ import annotations

import json as stdlib_json
from typing import Any, Dict, List, Optional, Sequence, Type, Union

_sentinel = object()


class AquiliaAssertions:
    """
    Mixin class providing Aquilia-specific assertion methods.

    Designed to be mixed into test case classes, but can also be used
    standalone::

        asserts = AquiliaAssertions()
        asserts.assert_status(response, 200)
    """

    # ------------------------------------------------------------------
    # Response status assertions
    # ------------------------------------------------------------------

    def assert_status(self, response, expected: int, msg: str = ""):
        """Assert HTTP status code."""
        actual = response.status_code
        assert actual == expected, (
            f"Expected status {expected}, got {actual}. "
            f"{msg}\nBody: {_body_preview(response)}"
        )

    def assert_status_in_range(self, response, low: int, high: int, msg: str = ""):
        """Assert status code is within [low, high) range."""
        actual = response.status_code
        assert low <= actual < high, (
            f"Expected status in [{low}, {high}), got {actual}. "
            f"{msg}\nBody: {_body_preview(response)}"
        )

    def assert_success(self, response, msg: str = ""):
        """Assert 2xx status."""
        assert response.is_success, (
            f"Expected 2xx, got {response.status_code}. "
            f"{msg}\nBody: {_body_preview(response)}"
        )

    def assert_created(self, response, msg: str = ""):
        """Assert 201 Created."""
        self.assert_status(response, 201, msg)

    def assert_accepted(self, response, msg: str = ""):
        """Assert 202 Accepted."""
        self.assert_status(response, 202, msg)

    def assert_no_content(self, response, msg: str = ""):
        """Assert 204 No Content."""
        self.assert_status(response, 204, msg)

    def assert_redirect(self, response, location: Optional[str] = None, msg: str = ""):
        """Assert 3xx redirect, optionally checking Location header."""
        assert response.is_redirect, (
            f"Expected 3xx redirect, got {response.status_code}. {msg}"
        )
        if location is not None:
            actual = response.header("location")
            assert actual == location, (
                f"Expected redirect to {location!r}, got {actual!r}"
            )

    def assert_permanent_redirect(self, response, location: Optional[str] = None, msg: str = ""):
        """Assert 301 Moved Permanently."""
        self.assert_status(response, 301, msg)
        if location is not None:
            actual = response.header("location")
            assert actual == location, (
                f"Expected redirect to {location!r}, got {actual!r}"
            )

    def assert_bad_request(self, response, msg: str = ""):
        """Assert 400."""
        self.assert_status(response, 400, msg)

    def assert_unauthorized(self, response, msg: str = ""):
        """Assert 401."""
        self.assert_status(response, 401, msg)

    def assert_forbidden(self, response, msg: str = ""):
        """Assert 403."""
        self.assert_status(response, 403, msg)

    def assert_not_found(self, response, msg: str = ""):
        """Assert 404."""
        self.assert_status(response, 404, msg)

    def assert_method_not_allowed(self, response, msg: str = ""):
        """Assert 405 Method Not Allowed."""
        self.assert_status(response, 405, msg)

    def assert_conflict(self, response, msg: str = ""):
        """Assert 409 Conflict."""
        self.assert_status(response, 409, msg)

    def assert_gone(self, response, msg: str = ""):
        """Assert 410 Gone."""
        self.assert_status(response, 410, msg)

    def assert_unprocessable(self, response, msg: str = ""):
        """Assert 422 Unprocessable Entity."""
        self.assert_status(response, 422, msg)

    def assert_too_many_requests(self, response, msg: str = ""):
        """Assert 429 Too Many Requests."""
        self.assert_status(response, 429, msg)

    def assert_server_error(self, response, msg: str = ""):
        """Assert 500 Internal Server Error."""
        self.assert_status(response, 500, msg)

    def assert_service_unavailable(self, response, msg: str = ""):
        """Assert 503 Service Unavailable."""
        self.assert_status(response, 503, msg)

    # ------------------------------------------------------------------
    # JSON assertions
    # ------------------------------------------------------------------

    def assert_json(self, response, expected: Any = None, msg: str = ""):
        """Assert response is JSON, optionally matching expected value."""
        ct = response.content_type
        assert "json" in ct, f"Expected JSON content-type, got {ct!r}. {msg}"
        if expected is not None:
            actual = response.json()
            assert actual == expected, (
                f"JSON mismatch.\nExpected: {expected}\nActual:   {actual}\n{msg}"
            )

    def assert_json_contains(self, response, subset: Dict[str, Any], msg: str = ""):
        """Assert JSON body contains all keys/values from *subset*."""
        actual = response.json()
        for key, expected_val in subset.items():
            assert key in actual, f"Missing key {key!r} in response JSON. {msg}"
            assert actual[key] == expected_val, (
                f"JSON key {key!r}: expected {expected_val!r}, got {actual[key]!r}. {msg}"
            )

    def assert_json_key(self, response, key: str, msg: str = ""):
        """Assert JSON body contains a specific key."""
        actual = response.json()
        assert key in actual, f"Key {key!r} not found in JSON response. {msg}"

    def assert_json_path(self, response, path: str, expected: Any = _sentinel, msg: str = ""):
        """
        Assert a deeply nested JSON value using dot-notation.

        Examples::

            asserts.assert_json_path(resp, "data.users.0.name", "Alice")
            asserts.assert_json_path(resp, "meta.pagination.total")  # just check exists
        """
        data = response.json()
        ref = data
        parts = path.split(".")
        for part in parts:
            if isinstance(ref, dict):
                assert part in ref, (
                    f"JSON path {path!r}: key {part!r} not found. "
                    f"Available keys: {list(ref.keys())}. {msg}"
                )
                ref = ref[part]
            elif isinstance(ref, (list, tuple)):
                try:
                    idx = int(part)
                except ValueError:
                    raise AssertionError(
                        f"JSON path {path!r}: expected int index, got {part!r}. {msg}"
                    )
                assert 0 <= idx < len(ref), (
                    f"JSON path {path!r}: index {idx} out of range (len={len(ref)}). {msg}"
                )
                ref = ref[idx]
            else:
                raise AssertionError(
                    f"JSON path {path!r}: cannot traverse into {type(ref).__name__}. {msg}"
                )
        if expected is not _sentinel:
            assert ref == expected, (
                f"JSON path {path!r}: expected {expected!r}, got {ref!r}. {msg}"
            )
        return ref

    def assert_json_list(self, response, min_length: Optional[int] = None, msg: str = ""):
        """Assert JSON body is a list, optionally with minimum length."""
        data = response.json()
        assert isinstance(data, list), (
            f"Expected JSON list, got {type(data).__name__}. {msg}"
        )
        if min_length is not None:
            assert len(data) >= min_length, (
                f"Expected list with >= {min_length} items, got {len(data)}. {msg}"
            )

    def assert_json_length(self, response, expected: int, msg: str = ""):
        """Assert JSON list/dict has exactly *expected* items/keys."""
        data = response.json()
        actual = len(data)
        assert actual == expected, (
            f"Expected JSON length {expected}, got {actual}. {msg}"
        )

    def assert_json_not_empty(self, response, msg: str = ""):
        """Assert JSON body is non-empty (non-null, non-empty list/dict)."""
        data = response.json()
        assert data, f"Expected non-empty JSON, got {data!r}. {msg}"

    # ------------------------------------------------------------------
    # Content type assertions
    # ------------------------------------------------------------------

    def assert_html(self, response, msg: str = ""):
        """Assert response is HTML."""
        ct = response.content_type
        assert "html" in ct, f"Expected HTML content-type, got {ct!r}. {msg}"

    def assert_content_type(self, response, expected: str, msg: str = ""):
        """Assert exact content type."""
        actual = response.content_type
        assert actual == expected, (
            f"Expected content-type {expected!r}, got {actual!r}. {msg}"
        )

    # ------------------------------------------------------------------
    # Header assertions
    # ------------------------------------------------------------------

    def assert_header(self, response, name: str, value: Optional[str] = None, msg: str = ""):
        """Assert response header exists (and optionally matches value)."""
        actual = response.header(name)
        assert actual is not None, f"Header {name!r} not found. {msg}"
        if value is not None:
            assert actual == value, (
                f"Header {name!r}: expected {value!r}, got {actual!r}. {msg}"
            )

    def assert_header_contains(self, response, name: str, substring: str, msg: str = ""):
        """Assert response header value contains a substring."""
        actual = response.header(name)
        assert actual is not None, f"Header {name!r} not found. {msg}"
        assert substring in actual, (
            f"Header {name!r}: expected to contain {substring!r}, got {actual!r}. {msg}"
        )

    def assert_no_header(self, response, name: str, msg: str = ""):
        """Assert response header does NOT exist."""
        actual = response.header(name)
        assert actual is None, f"Header {name!r} unexpectedly present: {actual!r}. {msg}"

    def assert_content_length(self, response, expected: Optional[int] = None, msg: str = ""):
        """Assert Content-Length header exists (and optionally matches)."""
        cl = response.header("content-length")
        assert cl is not None, f"Content-Length header not found. {msg}"
        if expected is not None:
            assert int(cl) == expected, (
                f"Content-Length: expected {expected}, got {cl}. {msg}"
            )

    # ------------------------------------------------------------------
    # Cookie assertions
    # ------------------------------------------------------------------

    def assert_cookie(self, response, name: str, msg: str = ""):
        """Assert Set-Cookie header contains the named cookie."""
        sc = response.header("set-cookie") or ""
        assert name in sc, f"Cookie {name!r} not found in Set-Cookie. {msg}"

    def assert_cookie_value(self, response, name: str, expected: str, msg: str = ""):
        """Assert a cookie's value in Set-Cookie header."""
        sc = response.header("set-cookie") or ""
        assert name in sc, f"Cookie {name!r} not found in Set-Cookie. {msg}"
        # Parse cookie value from Set-Cookie header
        for part in sc.split(","):
            part = part.strip()
            kv = part.split(";")[0]
            if "=" in kv:
                cname, _, cval = kv.partition("=")
                if cname.strip() == name:
                    assert cval.strip() == expected, (
                        f"Cookie {name!r}: expected {expected!r}, got {cval.strip()!r}. {msg}"
                    )
                    return
        raise AssertionError(f"Cookie {name!r} not found. {msg}")

    def assert_no_cookie(self, response, name: str, msg: str = ""):
        """Assert Set-Cookie does NOT contain the named cookie."""
        sc = response.header("set-cookie") or ""
        assert name not in sc, (
            f"Cookie {name!r} unexpectedly present in Set-Cookie. {msg}"
        )

    # ------------------------------------------------------------------
    # Body assertions
    # ------------------------------------------------------------------

    def assert_body_contains(self, response, text: str, msg: str = ""):
        """Assert text body contains substring."""
        body = response.text
        assert text in body, (
            f"Expected {text!r} in body, not found. {msg}\n"
            f"Body preview: {body[:300]}"
        )

    def assert_body_not_contains(self, response, text: str, msg: str = ""):
        """Assert text body does NOT contain substring."""
        body = response.text
        assert text not in body, (
            f"Unexpected {text!r} found in body. {msg}"
        )

    def assert_body_empty(self, response, msg: str = ""):
        """Assert response body is empty."""
        assert len(response.body) == 0, (
            f"Expected empty body, got {len(response.body)} bytes. {msg}"
        )

    # ------------------------------------------------------------------
    # Fault assertions
    # ------------------------------------------------------------------

    def assert_fault_raised(
        self,
        fault_engine_or_captured: Any,
        code: Optional[str] = None,
        domain: Optional[str] = None,
        msg: str = "",
    ):
        """Assert that a fault was emitted / captured."""
        faults = _extract_faults(fault_engine_or_captured)
        if code:
            matching = [f for f in faults if getattr(f, "code", None) == code]
            assert matching, (
                f"No fault with code {code!r} captured. "
                f"Captured: {[getattr(f, 'code', '?') for f in faults]}. {msg}"
            )
        elif domain:
            matching = [
                f for f in faults
                if str(getattr(f, "domain", "")) == domain
            ]
            assert matching, (
                f"No fault in domain {domain!r} captured. {msg}"
            )
        else:
            assert faults, f"No faults captured. {msg}"

    def assert_no_faults(self, fault_engine_or_captured: Any, msg: str = ""):
        """Assert no faults were captured."""
        faults = _extract_faults(fault_engine_or_captured)
        assert not faults, (
            f"Expected no faults, got {len(faults)}: "
            f"{[getattr(f, 'code', '?') for f in faults]}. {msg}"
        )

    def assert_fault_count(self, fault_engine_or_captured: Any, expected: int, msg: str = ""):
        """Assert exact number of faults captured."""
        faults = _extract_faults(fault_engine_or_captured)
        actual = len(faults)
        assert actual == expected, (
            f"Expected {expected} faults, got {actual}: "
            f"{[getattr(f, 'code', '?') for f in faults]}. {msg}"
        )

    def assert_fault_severity(
        self,
        fault_engine_or_captured: Any,
        severity: Any,
        code: Optional[str] = None,
        msg: str = "",
    ):
        """Assert fault(s) have the expected severity."""
        faults = _extract_faults(fault_engine_or_captured)
        if code:
            faults = [f for f in faults if getattr(f, "code", None) == code]
        assert faults, f"No matching faults found. {msg}"
        for f in faults:
            actual_sev = getattr(f, "severity", None)
            assert actual_sev == severity, (
                f"Fault {getattr(f, 'code', '?')}: expected severity "
                f"{severity!r}, got {actual_sev!r}. {msg}"
            )

    # ------------------------------------------------------------------
    # DI assertions
    # ------------------------------------------------------------------

    def assert_registered(self, container, token: Any, msg: str = ""):
        """Assert a service is registered in the DI container."""
        assert container.is_registered(token), (
            f"Token {token!r} not registered in container. {msg}"
        )

    def assert_not_registered(self, container, token: Any, msg: str = ""):
        """Assert a service is NOT registered in the DI container."""
        assert not container.is_registered(token), (
            f"Token {token!r} unexpectedly registered in container. {msg}"
        )

    def assert_resolves(self, container, token: Any, msg: str = ""):
        """Assert a service resolves successfully (sync)."""
        try:
            result = container.resolve(token)
            assert result is not None
        except Exception as exc:
            raise AssertionError(
                f"Token {token!r} failed to resolve: {exc}. {msg}"
            ) from exc

    async def assert_resolves_async(self, container, token: Any, msg: str = ""):
        """Assert a service resolves successfully (async)."""
        try:
            result = await container.resolve_async(token)
            assert result is not None
        except Exception as exc:
            raise AssertionError(
                f"Token {token!r} failed to resolve async: {exc}. {msg}"
            ) from exc

    # ------------------------------------------------------------------
    # Effect assertions
    # ------------------------------------------------------------------

    def assert_effect_acquired(self, provider: Any, count: Optional[int] = None, msg: str = ""):
        """Assert an effect provider's acquire was called."""
        actual = getattr(provider, "acquire_count", 0)
        if count is not None:
            assert actual == count, (
                f"Expected {count} acquire calls, got {actual}. {msg}"
            )
        else:
            assert actual > 0, f"Expected effect to be acquired, got 0 calls. {msg}"

    def assert_effect_released(self, provider: Any, count: Optional[int] = None, msg: str = ""):
        """Assert an effect provider's release was called."""
        actual = getattr(provider, "release_count", 0)
        if count is not None:
            assert actual == count, (
                f"Expected {count} release calls, got {actual}. {msg}"
            )
        else:
            assert actual > 0, f"Expected effect to be released, got 0 calls. {msg}"

    # ------------------------------------------------------------------
    # Cache assertions
    # ------------------------------------------------------------------

    async def assert_cache_hit(self, cache: Any, key: str, expected: Any = _sentinel, msg: str = ""):
        """Assert a cache key exists (and optionally matches value)."""
        value = await cache.get(key)
        assert value is not None, f"Cache miss for key {key!r}. {msg}"
        if expected is not _sentinel:
            assert value == expected, (
                f"Cache key {key!r}: expected {expected!r}, got {value!r}. {msg}"
            )

    async def assert_cache_miss(self, cache: Any, key: str, msg: str = ""):
        """Assert a cache key does NOT exist."""
        value = await cache.get(key)
        assert value is None, (
            f"Expected cache miss for key {key!r}, got {value!r}. {msg}"
        )

    # ------------------------------------------------------------------
    # Mail assertions
    # ------------------------------------------------------------------

    def assert_mail_count(self, outbox: Any, expected: int, msg: str = ""):
        """Assert exact number of messages in the mail outbox."""
        actual = len(outbox)
        assert actual == expected, (
            f"Expected {expected} mail messages, got {actual}. {msg}"
        )

    def assert_mail_to(self, outbox: Any, address: str, msg: str = ""):
        """Assert at least one message was sent to *address*."""
        matching = [m for m in outbox if address in m.to]
        assert matching, (
            f"No mail sent to {address!r}. "
            f"Recipients: {[m.to for m in outbox]}. {msg}"
        )

    def assert_mail_from(self, outbox: Any, address: str, msg: str = ""):
        """Assert at least one message was sent from *address*."""
        matching = [m for m in outbox if m.from_email == address]
        assert matching, (
            f"No mail from {address!r}. "
            f"Senders: {[m.from_email for m in outbox]}. {msg}"
        )


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _body_preview(response, max_len: int = 200) -> str:
    try:
        return response.text[:max_len]
    except Exception:
        return repr(response.body[:max_len])


def _extract_faults(obj) -> list:
    """Normalise fault source to a plain list."""
    if isinstance(obj, list):
        return obj
    if hasattr(obj, "captured"):
        return obj.captured
    if hasattr(obj, "faults"):
        return obj.faults
    return []
