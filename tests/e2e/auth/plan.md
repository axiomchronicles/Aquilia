# Auth E2E Regression Test Plan

## Overview
End-to-end regression tests for the AquilAuth system. All tests use in-memory stores and run without Docker.

## Test Modules

| Module | Tests | Coverage Area |
|--------|-------|---------------|
| `test_password_auth.py` | 10 | Password login, suspended/deleted users, rehash, MFA gate |
| `test_token_lifecycle.py` | 9 | Token issue/validate/expire/refresh/revoke/key rotation |
| `test_api_key_auth.py` | 10 | API key auth, expired/revoked keys, scope enforcement |
| `test_oauth2_flows.py` | 12 | Auth code + PKCE, client credentials, device flow |
| `test_mfa.py` | 9 | TOTP enroll/verify/time window, backup codes |
| `test_authorization.py` | 15 | RBAC, ABAC, scopes, tenants, policy builders |
| `test_guards.py` | 9 | AuthGuard, ScopeGuard, RoleGuard pipeline |
| `test_session_integration.py` | 9 | Store CRUD, session-token binding |
| `test_rate_limiting.py` | 4 | Lockout, reset, expiration |
| `test_regression_sequences.py` | 6 | Multi-step cross-component scenarios |

**Total: ~93 test cases**

## Execution

```bash
# Full suite
python -m pytest tests/e2e/auth/ -v --tb=short --junitxml=tests/e2e/auth/report.xml

# Single module
python -m pytest tests/e2e/auth/test_password_auth.py -v

# With coverage
python -m pytest tests/e2e/auth/ -v --cov=aquilia.auth --cov-report=term-missing
```

## Fixture Isolation
All fixtures are `function`-scoped. Each test gets fresh in-memory stores.
No shared state between tests. No external services required.
