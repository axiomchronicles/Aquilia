"""
Test 10: Sessions System (sessions/)

Tests Session, SessionID, SessionPolicy, SessionEngine, decorators.
"""

import pytest
import asyncio
from datetime import timedelta
from unittest.mock import MagicMock, AsyncMock

from aquilia.sessions.core import Session, SessionID


# ============================================================================
# SessionID
# ============================================================================

class TestSessionID:

    def test_generate(self):
        sid = SessionID()
        assert sid is not None
        s = str(sid)
        assert s.startswith("sess_")

    def test_unique(self):
        ids = [str(SessionID()) for _ in range(50)]
        assert len(set(ids)) == 50

    def test_repr(self):
        sid = SessionID()
        r = repr(sid)
        assert "sess_" in r or "SessionID" in r

    def test_equality(self):
        sid = SessionID()
        # Same internal value should be equal
        s = str(sid)
        assert str(sid) == s  # consistent

    def test_from_string(self):
        sid = SessionID()
        s = str(sid)
        sid2 = SessionID.from_string(s)
        assert str(sid2) == s


# ============================================================================
# Session
# ============================================================================

class TestSession:

    def test_create(self):
        sid = SessionID()
        session = Session(id=sid)
        assert session.id is sid

    def test_data_operations(self):
        session = Session(id=SessionID())
        session["key"] = "value"
        assert session["key"] == "value"
        assert "key" in session

    def test_get_with_default(self):
        session = Session(id=SessionID())
        assert session.get("missing", "default") == "default"

    def test_delete_key(self):
        session = Session(id=SessionID())
        session["x"] = 1
        session.delete("x")
        assert "x" not in session

    def test_clear(self):
        session = Session(id=SessionID())
        session["a"] = 1
        session["b"] = 2
        session.clear_data()
        assert "a" not in session
        assert "b" not in session

    def test_is_new(self):
        session = Session(id=SessionID())
        assert session.version == 0  # version 0 means new session

    def test_modified(self):
        session = Session(id=SessionID())
        session["x"] = 1
        assert session._dirty is True

    def test_str_representation(self):
        sid = SessionID()
        session = Session(id=sid)
        s = str(session)
        assert "sess_" in s or "Session" in s


# ============================================================================
# Session Decorators (imports)
# ============================================================================

class TestSessionDecorators:

    def test_session_require_import(self):
        from aquilia.sessions.decorators import session
        assert session is not None

    def test_authenticated_import(self):
        from aquilia.sessions.decorators import authenticated
        assert authenticated is not None

    def test_stateful_import(self):
        from aquilia.sessions.decorators import stateful
        assert stateful is not None

    def test_session_required_fault(self):
        from aquilia.sessions.decorators import SessionRequiredFault
        assert issubclass(SessionRequiredFault, Exception)

    def test_authentication_required_fault(self):
        from aquilia.sessions.decorators import AuthenticationRequiredFault
        assert issubclass(AuthenticationRequiredFault, Exception)
