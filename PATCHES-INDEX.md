# PATCHES-INDEX.md — Aquilia Fix Index

**Generated:** 2026-02-14  
**Based on:** CODEBASE-AUDIT.md (2026-02-13)

---

## Patch Summary

| Patch ID | Priority | Issue(s) | Files Changed | Test Files | Acceptance Command |
|----------|----------|----------|---------------|------------|-------------------|
| PR-Fix-C01 | 🔴 Critical | C-01, S-01 | `aquilia/middleware_ext/request_scope.py` | `tests/test_request_scope.py` | `pytest tests/test_request_scope.py -v` |
| PR-Fix-C02 | 🔴 Critical | C-02, S-02 | `aquilia/config_builders.py`, `aquilia/server.py` | `tests/test_auth_secret.py` | `pytest tests/test_auth_secret.py -v` |
| PR-Fix-C03 | 🔴 Critical | C-03 | `aquilia/di/providers.py` | `tests/test_lazy_proxy.py` | `pytest tests/test_lazy_proxy.py -v` |
| PR-Fix-C04 | 🔴 Critical | C-04 | `aquilia/__init__.py` | `tests/test_public_api.py` | `pytest tests/test_public_api.py -v` |
| PR-Fix-C05C06 | 🔴 Critical | C-05, C-06 | `pyproject.toml`, `setup.py`, `aquilia/__init__.py` | `tests/test_version.py` | `pytest tests/test_version.py -v` |
| PR-Fix-C07 | 🔴 Critical | C-07 | `pyproject.toml`, `setup.py` | (install test) | `pip install -e . && python -c "import cryptography, argon2, passlib"` |
| PR-Fix-F01 | 🟡 Medium | F-01 | `aquilia/middleware.py` | `tests/test_remaining_fixes.py::TestExceptionMiddlewareKeyError` | `pytest tests/test_remaining_fixes.py::TestExceptionMiddlewareKeyError -v` |
| PR-Fix-F02 | 🔴 High | F-02 | `aquilia/auth/authz.py` | `tests/test_remaining_fixes.py::TestRBACCycleDetection` | `pytest tests/test_remaining_fixes.py::TestRBACCycleDetection -v` |
| PR-Fix-S03S04 | 🔴 High | S-03, S-04 | `aquilia/auth/hashing.py` | `tests/test_remaining_fixes.py::TestAsyncPasswordHashing` | `pytest tests/test_remaining_fixes.py::TestAsyncPasswordHashing -v` |
| PR-Fix-Hashlib | 🔴 High | (pre-existing) | `aquilia/auth/hashing.py` | `tests/test_remaining_fixes.py::TestAsyncPasswordHashing` | PBKDF2 fallback works when argon2 is installed |
| PR-Fix-P03 | ⚠️ Low | P-03 | `aquilia/faults/engine.py` | `tests/test_remaining_fixes.py::TestFaultHistoryDeque` | `pytest tests/test_remaining_fixes.py::TestFaultHistoryDeque -v` |
| PR-Fix-I01 | 🔴 Critical | I-01 | `.github/workflows/ci.yml` | (CI itself) | Push to branch and check Actions tab |
| PR-Fix-I02 | 🟡 Medium | I-02 | `.env.example` | (docs) | `cat .env.example` |
| PR-Fix-Hygiene | ⚠️ Low | F-05, F-06 | `.gitignore`, removed: `response.py.backup`, `response.py.old`, `p.html` | N/A | `ls aquilia/response.py.backup 2>/dev/null; echo $?` (should be 1) |

---

## New Files Created

| File | Purpose |
|------|---------|
| `tests/test_request_scope.py` | DI isolation tests (C-01) |
| `tests/test_auth_secret.py` | Secret rejection tests (C-02) |
| `tests/test_lazy_proxy.py` | LazyProxy crash tests (C-03) |
| `tests/test_public_api.py` | `__all__` validation tests (C-04) |
| `tests/test_version.py` | Version/entrypoint sync tests (C-05, C-06) |
| `tests/test_remaining_fixes.py` | F-01, F-02, S-03/S-04, P-03 tests |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline |
| `.env.example` | Environment variable documentation |
| `verify_changes.sh` | Full verification script |
| `PATCHES-INDEX.md` | This file |

---

## Quick Apply — All Patches at Once

All patches have been applied directly to the working tree. To verify:

```bash
# Run the full verification script
./verify_changes.sh

# Or run just the priority tests
pytest tests/test_request_scope.py \
       tests/test_auth_secret.py \
       tests/test_lazy_proxy.py \
       tests/test_public_api.py \
       tests/test_version.py \
       tests/test_remaining_fixes.py \
       -v --tb=short
```

To commit all changes:

```bash
git add -A
git commit -m "fix: apply all audit remediation patches (C-01 through P-03)

- C-01: Fix request-scope DI isolation (create_request_scope)
- C-02: Remove hardcoded insecure secret; reject in non-dev mode
- C-03: Fix LazyProxy run_until_complete crash in async context
- C-04: Remove phantom exports from __all__
- C-05/C-06: Synchronize version to 0.2.0; fix CLI entrypoint
- C-07: Add missing dependencies (cryptography, argon2-cffi, passlib)
- F-01: Remove KeyError→404 mapping in ExceptionMiddleware
- F-02: Add cycle detection to RBAC get_permissions
- S-03/S-04: Add async password hashing and breach check wrappers
- P-03: Replace list.pop(0) with deque in fault history
- I-01: Add GitHub Actions CI pipeline
- I-02: Add .env.example
- Hygiene: Remove backup files, update .gitignore
"
```

---

## Rollback Instructions

### If C-01 breaks request handling:
The previous behavior was `request_container = app_container` (shared container). Revert:
```bash
git checkout HEAD -- aquilia/middleware_ext/request_scope.py
```
**Risk:** Low. The `create_request_scope()` method already exists and is used by `server.py:164`.

### If C-02 breaks dev startup:
In DEV mode, the insecure secret is still allowed. If you need the old behavior temporarily:
```bash
git checkout HEAD -- aquilia/config_builders.py aquilia/server.py
```

### If C-04 breaks imports:
The removed names were never importable (commented out). Revert:
```bash
git checkout HEAD -- aquilia/__init__.py
```

### If C-05/C-06 breaks packaging:
```bash
git checkout HEAD -- pyproject.toml setup.py aquilia/__init__.py
```

---

## Migration Notes

### C-02: AuthConfig.secret_key default changed
**Before:** `secret_key: str = "aquilia_insecure_dev_secret"`  
**After:** `secret_key: Optional[str] = None`  
**Action:** Any code relying on the default secret must now explicitly set a key. In DEV mode, the server still starts (with a warning). In PROD/STAGING, it raises `ValueError`.

### C-04: `require_auth`, `require_scopes`, `require_roles` removed from `__all__`
These were never importable (source imports were commented out). No working code should be affected.

### C-05/C-06: Version bumped to 0.2.0
All three sources (`pyproject.toml`, `setup.py`, `__init__.py`) now report `0.2.0`.

### F-01: KeyError no longer caught as 404
**Before:** Any `KeyError` in handler → 404  
**After:** `KeyError` falls through to generic `Exception` → 500  
**Action:** If you intentionally raised `KeyError` for 404, switch to raising a `Fault` with `FaultDomain.ROUTING` or return `Response.json({"error": "Not found"}, status=404)` explicitly.

---

## Coverage Plan

### Short-term targets (2-4 weeks)

| Area | Current | Target | Estimated Tests to Add |
|------|---------|--------|----------------------|
| DI Container | 0% | 80% | ~40 tests |
| Auth System | 0% | 60% | ~35 tests |
| Sessions | 0% | 50% | ~25 tests |
| Controllers | 0% | 50% | ~20 tests |
| Middleware | ~5% | 60% | ~15 tests |

### Suggested test fixtures:

```python
# conftest.py additions
@pytest.fixture
def di_container():
    """Fresh DI container for testing."""
    from aquilia.di import Container
    return Container(scope="test")

@pytest.fixture
def password_hasher():
    """PBKDF2 hasher (no argon2 dep needed)."""
    from aquilia.auth.hashing import PasswordHasher
    return PasswordHasher(algorithm="pbkdf2_sha256", iterations=1000)

@pytest.fixture
def rbac_engine():
    """RBAC engine with basic roles."""
    from aquilia.auth.authz import RBACEngine
    engine = RBACEngine()
    engine.define_role("viewer", ["read"])
    engine.define_role("editor", ["write"], inherits=["viewer"])
    engine.define_role("admin", ["delete", "manage"], inherits=["editor"])
    return engine
```

### Run only new tests:
```bash
pytest tests/test_request_scope.py tests/test_auth_secret.py tests/test_lazy_proxy.py tests/test_public_api.py tests/test_version.py tests/test_remaining_fixes.py -v
```

---

## NEEDS RUNTIME Items

| Item | Diagnostic Command | Notes |
|------|-------------------|-------|
| F-04: `aquila_sockets` init order | `python -c "from aquilia import AquiliaServer; s = AquiliaServer.__new__(AquiliaServer); print(hasattr(s, 'aquila_sockets'))"` | May require full workspace config to trigger |
| S-05: JWT algorithm confusion | Generate ephemeral RSA key: `python -c "from cryptography.hazmat.primitives.asymmetric import rsa; k = rsa.generate_private_key(65537, 2048); print('OK')"` | Need to verify custom JWT impl accepts `alg: none` |
| I-04: Full mypy run | `mypy aquilia/ --ignore-missing-imports` | May produce many errors on first run |
| F-03: datetime.utcnow() count | `grep -rn "utcnow()" aquilia/ --include="*.py" \| wc -l` | ~20 occurrences to fix |
