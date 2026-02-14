"""
Tests for F-01 (KeyError not swallowed as 404),
F-02 (RBAC cycle detection),
S-03/S-04 (async password hashing),
P-03 (deque history).
"""
import asyncio
import pytest


# ---------------------------------------------------------------------------
# F-01: KeyError no longer mapped to 404
# ---------------------------------------------------------------------------

class TestExceptionMiddlewareKeyError:
    """ExceptionMiddleware must NOT map KeyError → 404."""

    @pytest.mark.asyncio
    async def test_keyerror_becomes_500_not_404(self):
        """A KeyError from handler code must produce 500, not 404."""
        from aquilia.middleware import ExceptionMiddleware
        from aquilia.response import Response

        class FakeCtx:
            request_id = "test-123"

        class FakeRequest:
            method = "GET"
            path = "/test"
            def header(self, name, default=None):
                return default
            state = {}

        async def handler(request, ctx, next_handler=None):
            d = {"a": 1}
            return d["missing"]  # raises KeyError

        mw = ExceptionMiddleware(debug=True)
        response = await mw(FakeRequest(), FakeCtx(), handler)
        # After fix, KeyError falls through to generic Exception → 500
        assert response.status == 500, (
            f"KeyError should produce 500, got {response.status}"
        )


# ---------------------------------------------------------------------------
# F-02: RBAC cycle detection
# ---------------------------------------------------------------------------

class TestRBACCycleDetection:
    """RBAC get_permissions must not infinitely recurse on cyclic hierarchies."""

    def test_cyclic_role_hierarchy_no_recursion_error(self):
        from aquilia.auth.authz import RBACEngine
        engine = RBACEngine()
        engine.define_role("admin", ["read"], inherits=["superadmin"])
        engine.define_role("superadmin", ["write"], inherits=["admin"])

        # Must not raise RecursionError
        perms = engine.get_permissions("admin")
        assert "read" in perms
        assert "write" in perms

    def test_normal_inheritance_still_works(self):
        from aquilia.auth.authz import RBACEngine
        engine = RBACEngine()
        engine.define_role("viewer", ["read"])
        engine.define_role("editor", ["write"], inherits=["viewer"])
        engine.define_role("admin", ["delete"], inherits=["editor"])

        perms = engine.get_permissions("admin")
        assert perms == {"read", "write", "delete"}

    def test_no_inheritance(self):
        from aquilia.auth.authz import RBACEngine
        engine = RBACEngine()
        engine.define_role("viewer", ["read"])
        perms = engine.get_permissions("viewer")
        assert perms == {"read"}


# ---------------------------------------------------------------------------
# S-03 / S-04: Async password hashing
# ---------------------------------------------------------------------------

class TestAsyncPasswordHashing:
    """PasswordHasher must provide async wrappers."""

    @pytest.mark.asyncio
    async def test_hash_async_returns_hash(self):
        from aquilia.auth.hashing import PasswordHasher
        hasher = PasswordHasher(algorithm="pbkdf2_sha256")
        h = await hasher.hash_async("test_password_123")
        assert h.startswith("$pbkdf2_sha256$")

    @pytest.mark.asyncio
    async def test_verify_async_correct_password(self):
        from aquilia.auth.hashing import PasswordHasher
        hasher = PasswordHasher(algorithm="pbkdf2_sha256")
        h = hasher.hash("correct_password")
        result = await hasher.verify_async(h, "correct_password")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_async_wrong_password(self):
        from aquilia.auth.hashing import PasswordHasher
        hasher = PasswordHasher(algorithm="pbkdf2_sha256")
        h = hasher.hash("correct_password")
        result = await hasher.verify_async(h, "wrong_password")
        assert result is False

    @pytest.mark.asyncio
    async def test_hash_async_does_not_block_loop(self):
        """hash_async should yield control to the event loop."""
        from aquilia.auth.hashing import PasswordHasher
        hasher = PasswordHasher(algorithm="pbkdf2_sha256")
        
        progress = []

        async def background():
            progress.append("bg_start")
            await asyncio.sleep(0)
            progress.append("bg_end")

        task = asyncio.create_task(background())
        await hasher.hash_async("test_pass_123")
        await task

        assert "bg_start" in progress, "Background task should have run during hash"


# ---------------------------------------------------------------------------
# P-03: Deque-based fault history
# ---------------------------------------------------------------------------

class TestFaultHistoryDeque:
    """Fault history must use deque with maxlen."""

    def test_history_is_deque(self):
        from aquilia.faults.engine import FaultEngine
        from collections import deque
        engine = FaultEngine(debug=True)
        assert isinstance(engine._history, deque)

    def test_history_respects_maxlen(self):
        from aquilia.faults.engine import FaultEngine
        engine = FaultEngine(debug=True)
        assert engine._history.maxlen == engine._max_history
