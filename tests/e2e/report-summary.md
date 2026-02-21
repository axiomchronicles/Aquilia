# Auth E2E Regression Test Report

**Date:** 2026-02-21
**Suite:** `tests/e2e/auth/` (14 modules)
**Result:** ✅ **138 passed** | 0 failed | 0 errors | 0 skipped
**Duration:** 87.24s

## Summary by Module

| Module | Tests | Category | Status |
|--------|-------|----------|--------|
| `test_password_auth` | 10 | Regression | ✅ |
| `test_token_lifecycle` | 12 | Regression | ✅ |
| `test_api_key_auth` | 10 | Regression | ✅ |
| `test_oauth2_flows` | 11 | Regression | ✅ |
| `test_mfa` | 9 | Regression | ✅ |
| `test_authorization` | 19 | Regression | ✅ |
| `test_guards` | 9 | Regression | ✅ |
| `test_session_integration` | 11 | Regression | ✅ |
| `test_rate_limiting` | 5 | Regression | ✅ |
| `test_regression_sequences` | 6 | Regression | ✅ |
| `test_chaos` | 9 | Chaos | ✅ |
| `test_fuzz` | 14 | Fuzzing | ✅ |
| `test_stress` | 8 | Stress/Perf | ✅ |
| `test_fault_injection` | 5 | Fault Injection | ✅ |

## Bugs Found & Fixed

| # | Bug | File | Fix | Risk |
|---|-----|------|-----|------|
| 1 | `issue_access_token()` called with unsupported `client_id=` kwarg | `aquilia/auth/oauth.py` (3 sites) | Removed `client_id=` from all calls | high |
| 2 | `validate_refresh_token()` didn't check revocation status | `aquilia/auth/tokens.py` | Added `is_token_revoked()` check before returning data | high |
| 3 | `RateLimiter.is_locked_out()` didn't handle `max_attempts<=0` | `aquilia/auth/manager.py` | Added early return `True` for `max_attempts <= 0` | medium |

## Fuzz Results

- **Token parser:** 1000 random byte tokens, massive (1MB) tokens, invalid base64, forged signatures, empty/null tokens → **all rejected safely, zero crashes**
- **PKCE verifier:** 500 random verifiers → **all rejected safely**
- **Password policy (Hypothesis):** 500 random strings → **never crashed, always returned well-formed result**
- Crash log: `tests/e2e/fuzz-reports/` (empty — no crashes found)

## Performance Results

- **200 concurrent login+refresh:** All 200 completed successfully, no deadlocks
- **1000 token validations:** Completed within time budget
- **100 concurrent revocations:** All tokens properly revoked, store consistent
- **10000 tokens memory pressure:** Operations remain stable after bulk fill

## Steps Not Executable Locally

| Step | Reason | Mitigation |
|------|--------|------------|
| Kill DB mid-transaction | No external DB used — all in-memory stores | Simulated via monkey-patching store methods to raise exceptions (test_chaos.py) |
| Network throttling with packet loss | Requires tc/netem (Linux only) | Simulated via asyncio.wait_for timeout (test_fault_injection.py) |
| File upload fuzzing | No file upload endpoint in auth module | N/A — auth module is token/credential only |
| Background job failure (email) | No background job framework installed | Simulated timeout in store operations |

## Reproduction

```bash
python3 -m pytest tests/e2e/auth/ -v --tb=short --junitxml=tests/e2e/report.xml
```
