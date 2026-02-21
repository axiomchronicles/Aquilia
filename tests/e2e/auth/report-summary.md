# Auth E2E Regression Test Report

**Date:** 2026-02-21  
**Suite:** `tests/e2e/auth/`  
**Result:** ✅ **102 passed** | 0 failed | 0 errors | 0 skipped  
**Duration:** 10.29s

## Summary by Module

| Module | Tests | Status |
|--------|-------|--------|
| `test_password_auth` | 10 | ✅ |
| `test_token_lifecycle` | 12 | ✅ |
| `test_api_key_auth` | 10 | ✅ |
| `test_oauth2_flows` | 11 | ✅ |
| `test_mfa` | 9 | ✅ |
| `test_authorization` | 19 | ✅ |
| `test_guards` | 9 | ✅ |
| `test_session_integration` | 11 | ✅ |
| `test_rate_limiting` | 5 | ✅ |
| `test_regression_sequences` | 6 | ✅ |

## Bugs Found & Fixed

| Bug | File | Fix |
|-----|------|-----|
| `issue_access_token()` called with unsupported `client_id=` kwarg | `aquilia/auth/oauth.py` (3 sites) | Removed `client_id=` from all calls |
| `validate_refresh_token()` didn't check revocation status | `aquilia/auth/tokens.py` | Added `is_token_revoked()` check |

## Reproduction

```bash
python3 -m pytest tests/e2e/auth/ -v --tb=short --junitxml=tests/e2e/auth/report.xml
```
