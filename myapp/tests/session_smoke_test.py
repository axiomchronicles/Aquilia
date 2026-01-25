import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Any

# Core
from aquilia.sessions.core import (
    Session,
    SessionID,
    SessionPrincipal,
    SessionScope,
    SessionFlag,
)

# Policy
from aquilia.sessions.policy import (
    SessionPolicy,
    PersistencePolicy,
    ConcurrencyPolicy,
    TransportPolicy,
)

# Store
from aquilia.sessions.store import (
    MemoryStore,
    FileStore,
)

# Transport
from aquilia.sessions.transport import (
    CookieTransport,
    HeaderTransport,
    create_transport,
)

# Engine
from aquilia.sessions.engine import SessionEngine

# Faults
from aquilia.sessions.faults import (
    SessionFault,
    SessionExpiredFault,
    SessionInvalidFault,
    SessionConcurrencyViolationFault,
    SessionStoreUnavailableFault,
    SessionRotationFailedFault,
    SessionPolicyViolationFault,
)

# Decorators
from aquilia.sessions.decorators import (
    session as session_decorator,
    authenticated,
    stateful,
    SessionRequiredFault,
    AuthenticationRequiredFault,
)

# State
from aquilia.sessions.state import (
    SessionState,
    Field,
    CartState,
    UserPreferencesState,
)

# Enhanced
from aquilia.sessions.enhanced import (
    SessionContext,
    SessionGuard,
    requires,
    AdminGuard,
    VerifiedEmailGuard,
)

# Mocking for Transport tests
class MockRequest:
    def __init__(self, headers=None):
        self._headers = headers or {}
        self.state = {}
        self.path = "/"
        self.method = "GET"
        self.client = ("127.0.0.1", 12345)
    def header(self, name):
        return self._headers.get(name.lower())

class MockResponse:
    def __init__(self):
        self.headers = {}
        self.cookies = {}
    def set_cookie(self, key, value, **kwargs):
        self.cookies[key] = value
    def delete_cookie(self, key, **kwargs):
        self.cookies.pop(key, None)

async def test_core():
    print("Testing Core...")
    sid = SessionID()
    assert str(sid).startswith("sess_")
    
    principal = SessionPrincipal(kind="user", id="user1", attributes={"role": "admin"})
    assert principal.is_user()
    assert principal.get_attribute("role") == "admin"
    
    sess = Session(id=sid, principal=principal, scope=SessionScope.USER)
    assert not sess.is_dirty
    sess.set("foo", "bar")
    assert sess.is_dirty
    assert sess.get("foo") == "bar"
    
    sess_dict = sess.to_dict()
    sess_back = Session.from_dict(sess_dict)
    assert sess_back.id == sess.id
    assert sess_back.get("foo") == "bar"
    print("Core tests passed!")

async def test_policy():
    print("Testing Policy...")
    policy = SessionPolicy.for_web_users() \
        .lasting(days=7) \
        .idle_timeout(minutes=30) \
        .max_concurrent(3) \
        .build()
    
    assert policy.ttl == timedelta(days=7)
    assert policy.concurrency.max_sessions_per_principal == 3
    
    sess = Session(id=SessionID())
    assert policy.is_valid(sess)[0]
    
    sess.expires_at = datetime.utcnow() - timedelta(seconds=1)
    assert not policy.is_valid(sess)[0]
    print("Policy tests passed!")

async def test_stores():
    print("Testing Stores...")
    # MemoryStore
    mem_store = MemoryStore()
    sess = Session(id=SessionID())
    sess.set("data", "mem")
    await mem_store.save(sess)
    loaded = await mem_store.load(sess.id)
    assert loaded.get("data") == "mem"
    
    # FileStore
    tmpdir = tempfile.mkdtemp()
    try:
        file_store = FileStore(tmpdir)
        sess = Session(id=SessionID())
        sess.set("data", "file")
        await file_store.save(sess)
        loaded = await file_store.load(sess.id)
        assert loaded.get("data") == "file"
    finally:
        shutil.rmtree(tmpdir)
    print("Store tests passed!")

async def test_transport():
    print("Testing Transport...")
    policy = TransportPolicy(adapter="cookie", cookie_name="test_sess")
    transport = create_transport(policy)
    assert isinstance(transport, CookieTransport)
    
    req = MockRequest(headers={"cookie": "test_sess=sess_123"})
    assert transport.extract(req) == "sess_123"
    
    res = MockResponse()
    sess = Session(id=SessionID())
    transport.inject(res, sess) # Should not crash
    
    header_policy = TransportPolicy(adapter="header", header_name="X-Sess")
    header_transport = create_transport(header_policy)
    assert isinstance(header_transport, HeaderTransport)
    print("Transport tests passed!")

async def test_engine():
    print("Testing Engine...")
    policy = SessionPolicy.for_web_users().build()
    store = MemoryStore()
    transport = CookieTransport(policy.transport)
    engine = SessionEngine(policy, store, transport)
    
    req = MockRequest()
    sess = await engine.resolve(req)
    assert sess is not None
    
    old_id = sess.id
    sess.mark_authenticated(SessionPrincipal(kind="user", id="u1"))
    res = MockResponse()
    await engine.commit(sess, res, privilege_changed=True)
    
    # Rotation should have happened: old ID deleted, new ID in response
    assert not await store.exists(old_id)
    new_id_str = res.cookies.get(policy.transport.cookie_name)
    assert new_id_str is not None
    assert new_id_str != str(old_id)
    
    new_id = SessionID.from_string(new_id_str)
    assert await store.exists(new_id)
    print("Engine tests passed!")

async def test_state():
    print("Testing State...")
    data = {"items": ["apple"], "theme": "dark"}
    cart = CartState(data)
    assert cart.items == ["apple"]
    cart.items.append("banana")
    assert data["items"] == ["apple", "banana"]
    
    prefs = UserPreferencesState(data)
    assert prefs.theme == "dark"
    prefs.theme = "light"
    assert data["theme"] == "light"
    print("State tests passed!")

async def test_enhanced():
    print("Testing Enhanced...")
    # Guards
    admin_guard = AdminGuard()
    sess = Session(id=SessionID())
    assert not await admin_guard.check(sess)
    
    sess.mark_authenticated(SessionPrincipal(kind="user", id="admin", attributes={"role": "admin"}))
    assert await admin_guard.check(sess)
    
    email_guard = VerifiedEmailGuard()
    assert not await email_guard.check(sess)
    sess.principal.attributes["email_verified"] = True
    assert await email_guard.check(sess)
    
    # Context managers
    class MockCtx:
        def __init__(self, s):
            self.request = MockRequest()
            self.request.state["session"] = s
            
    ctx = MockCtx(sess)
    async with SessionContext.authenticated(ctx) as s:
        assert s == sess
        
    async with SessionContext.transactional(ctx) as s:
        s.set("temp", "value")
        # Snapshot taken
        
    try:
        async with SessionContext.transactional(ctx) as s:
            s.set("bad", "data")
            raise ValueError("abort")
    except ValueError:
        assert "bad" not in sess.data
        
    print("Enhanced tests passed!")

async def run_all():
    await test_core()
    await test_policy()
    await test_stores()
    await test_transport()
    await test_engine()
    await test_state()
    await test_enhanced()
    print("\n✅ ALL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_all())
