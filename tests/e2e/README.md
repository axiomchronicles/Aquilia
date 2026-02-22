# E2E Controller Regression Tests

## Overview

Comprehensive integration test suite for all controllers in the Aquilia `authentication` app.

**Test files:** `tests/e2e/controllers/`

| File | Tests | Category | Risk |
|------|-------|----------|------|
| `test_registration.py` | 8 | Auth flow | Medium |
| `test_auth_login.py` | 9 | Auth + sessions + cookies | High |
| `test_token_refresh.py` | 7 | Token rotation | High |
| `test_token_revocation.py` | 2 | Token revocation | High |
| `test_me_endpoint.py` | 7 | Bearer auth + cache | Medium |
| `test_session_management.py` | 5 | Sessions + decorators | High |
| `test_cache_sensitive.py` | 3 | Cache fallback | Medium |
| `test_template_rendering.py` | 5 | Template injection + XSS | High |
| `test_dashboard_crud.py` | 10 | CRUD + faults | Medium |
| `test_file_uploads.py` | 6 | Multipart + security | High |
| `test_chaos.py` | 3 | Race conditions | High |
| `test_fuzz.py` | 5 | Hypothesis fuzzing | High |
| `test_stress.py` | 2 | Concurrency | High |

## Quick Start

```bash
# Install dependencies
pip install -e .
pip install pytest pytest-asyncio pytest-timeout hypothesis

# Run all tests
python -m pytest tests/e2e/controllers/ -v --tb=short

# Run with JUnit report
python -m pytest tests/e2e/controllers/ -v --tb=short --junitxml=tests/e2e/report.xml

# Run a specific file
python -m pytest tests/e2e/controllers/test_registration.py -v

# Run only fast tests (skip stress/fuzz)
python -m pytest tests/e2e/controllers/ -v -k "not stress and not fuzz and not chaos"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AQUILIA_ENV` | `test` | Run mode |
| `REDIS_URL` | N/A | Redis URL (optional, for Redis-backed tests) |
| `PYTHONDONTWRITEBYTECODE` | `1` | Disable .pyc files |

## Docker Compose

```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Debugging Tips

1. **Import errors**: Ensure you've installed aquilia: `pip install -e .`
2. **Fixture errors**: The `test_server` fixture boots the full app — check `workspace.py` for syntax errors
3. **Template errors**: Ensure `authentication/templates/auth/` contains `register.html`, `login.html`, `dashboard.html`
4. **Slow tests**: Use `-k "not stress and not fuzz"` to skip heavy tests
5. **Hypothesis flakes**: Use `--hypothesis-seed=0` for deterministic fuzz runs

## Architecture

```
tests/
├── conftest.py              # sys.path setup
└── e2e/
    ├── conftest.py          # TestServer + TestClient fixtures
    ├── manifest.json        # Scope inventory
    ├── static-analysis.json # Static analysis findings
    ├── plan.md              # Test plan
    ├── README.md            # This file
    └── controllers/         # Test implementations
        ├── test_registration.py
        ├── test_auth_login.py
        ├── test_token_refresh.py
        ├── test_token_revocation.py
        ├── test_me_endpoint.py
        ├── test_session_management.py
        ├── test_cache_sensitive.py
        ├── test_template_rendering.py
        ├── test_dashboard_crud.py
        ├── test_file_uploads.py
        ├── test_chaos.py
        ├── test_fuzz.py
        └── test_stress.py
```
