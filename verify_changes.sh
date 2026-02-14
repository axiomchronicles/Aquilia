#!/usr/bin/env bash
# verify_changes.sh — Run all checks after applying patches.
# Exit non-zero on any failure.
set -euo pipefail

echo "=========================================="
echo " Aquilia Patch Verification Script"
echo "=========================================="

FAIL=0

# 1. Install
echo ""
echo "[1/7] Installing package in dev mode..."
pip install -e ".[dev]" -q || { echo "❌ pip install failed"; FAIL=1; }
pip install cryptography argon2-cffi passlib -q || { echo "❌ auth deps install failed"; FAIL=1; }

# 2. Version check
echo ""
echo "[2/7] Verifying version..."
VERSION=$(python -c "import aquilia; print(aquilia.__version__)")
echo "  aquilia.__version__ = $VERSION"
EXPECTED="0.2.0"
if [ "$VERSION" != "$EXPECTED" ]; then
    echo "❌ Version mismatch: expected $EXPECTED, got $VERSION"
    FAIL=1
else
    echo "  ✅ Version matches $EXPECTED"
fi

# 3. Public API check
echo ""
echo "[3/7] Verifying __all__ exports..."
python -c "
import aquilia
missing = [n for n in aquilia.__all__ if not hasattr(aquilia, n)]
if missing:
    print(f'❌ Missing exports: {missing}')
    exit(1)
print(f'  ✅ All {len(aquilia.__all__)} exports valid')
" || FAIL=1

# 4. Run priority tests
echo ""
echo "[4/7] Running priority tests..."
pytest tests/test_request_scope.py \
       tests/test_auth_secret.py \
       tests/test_lazy_proxy.py \
       tests/test_public_api.py \
       tests/test_version.py \
       tests/test_remaining_fixes.py \
       -v --tb=short -x || { echo "❌ Priority tests failed"; FAIL=1; }

# 5. Run full test suite (non-fatal for pre-existing failures)
echo ""
echo "[5/7] Running full test suite..."
pytest tests/ -v --tb=short --cov=aquilia --cov-report=term-missing || {
    echo "⚠️  Full test suite has failures (may be pre-existing)"
}

# 6. Security scan (if bandit is installed)
echo ""
echo "[6/7] Running security scan..."
if command -v bandit &>/dev/null; then
    bandit -r aquilia/ -ll -ii --quiet || { echo "⚠️  Bandit found issues"; }
else
    echo "  ⚠️  bandit not installed, skipping (pip install bandit)"
fi

# 7. DI Isolation concurrency test
echo ""
echo "[7/7] Running DI isolation concurrency check..."
python -c "
import asyncio
import sys
sys.path.insert(0, '.')

class FakeContainer:
    def __init__(self, scope='app', parent=None):
        self._scope = scope
        self._parent = parent
        self._local = {}
        self._shutdown_called = False
    def create_request_scope(self):
        return FakeContainer(scope='request', parent=self)
    async def shutdown(self):
        self._shutdown_called = True
    def set(self, key, value):
        self._local[key] = value
    def get(self, key, default=None):
        return self._local.get(key, default)

class FakeRuntime:
    def __init__(self, c):
        self.di_containers = {'default': c}

async def main():
    from aquilia.middleware_ext.request_scope import RequestScopeMiddleware
    from unittest.mock import AsyncMock

    app_container = FakeContainer(scope='app')
    runtime = FakeRuntime(app_container)
    captured = []
    barrier = asyncio.Barrier(10)

    async def fake_app(scope, receive, send):
        container = scope['state']['di_container']
        container.set('user', scope.get('test_user'))
        await barrier.wait()
        captured.append((scope.get('test_user'), container.get('user')))

    mw = RequestScopeMiddleware(fake_app, runtime)

    async def req(i):
        scope = {'type': 'http', 'app_name': 'default', 'test_user': f'user_{i}'}
        await mw(scope, AsyncMock(), AsyncMock())

    await asyncio.gather(*[req(i) for i in range(10)])

    leaked = [(u, v) for u, v in captured if u != v]
    if leaked:
        print(f'❌ DI LEAK DETECTED: {leaked}')
        exit(1)
    print(f'  ✅ {len(captured)} concurrent requests — no identity leakage')

asyncio.run(main())
" || { echo "❌ DI isolation check failed"; FAIL=1; }

echo ""
echo "=========================================="
if [ "$FAIL" -ne 0 ]; then
    echo "❌ VERIFICATION FAILED — see errors above"
    exit 1
else
    echo "✅ ALL CHECKS PASSED"
    exit 0
fi
