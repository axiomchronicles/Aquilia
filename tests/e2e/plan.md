# E2E Test Plan — Controllers + DI Regression Suite

## Overview

This plan covers **14 existing controller tests** and **13 new DI-specific tests** plus chaos/fuzz/stress scenarios exercising the full Aquilia DI system and its controller integration.

---

## Existing Controller Tests

| File | Coverage |
|------|----------|
| `test_auth_login.py` | Login flow, token issuance, invalid credentials |
| `test_registration.py` | User registration, duplicate detection, validation |
| `test_me_endpoint.py` | Authenticated /me endpoint |
| `test_token_refresh.py` | Token rotation, expired refresh |
| `test_token_revocation.py` | Token revocation |
| `test_session_management.py` | Session create/read/invalidate |
| `test_dashboard_crud.py` | Dashboard CRUD operations |
| `test_template_rendering.py` | Template rendering via controllers |
| `test_cache_sensitive.py` | Cache behavior, invalidation |
| `test_file_uploads.py` | Multipart uploads |
| `test_chaos.py` | Chaos scenarios (cache corruption, DB kill) |
| `test_fuzz.py` | Token parser fuzzing |
| `test_stress.py` | Concurrency/stress |

---

## DI Test Plan

### DI-01: Provider resolution (risk: low)
- **Target**: `Container.resolve_async`, `ValueProvider`, `ClassProvider`
- **Test**: Register token → resolve → verify correct instance and methods work
- **File**: `tests/e2e/di/test_di_resolution.py`

### DI-02: Singleton vs transient (risk: medium)
- **Target**: `Container._cache`, scope behavior
- **Test**: Singleton → `id(a) == id(b)`;  transient → `id(a) != id(b)`
- **File**: `tests/e2e/di/test_di_resolution.py`

### DI-03: Request-scoped providers (risk: high)
- **Target**: `Container.create_request_scope`, request cache isolation
- **Test**: Two request scopes → unique instances; shutdown clears cache
- **File**: `tests/e2e/di/test_di_resolution.py`

### DI-04: Lifecycle hooks (risk: medium)
- **Target**: `Lifecycle.on_startup`, `on_shutdown`, `register_finalizer`
- **Test**: Priority ordering, LIFO/FIFO/parallel finalizers, failure tolerance
- **File**: `tests/e2e/di/test_di_lifecycle.py`

### DI-05: Factory provider errors (risk: high)
- **Target**: Factory `instantiate` raising → no partial cache
- **Test**: First call fails, not cached; second call succeeds
- **File**: `tests/e2e/di/test_di_errors.py`

### DI-06: Missing binding (risk: medium)
- **Target**: `ProviderNotFoundError`, optional resolution
- **Test**: Resolve missing → error with token name; optional → None
- **File**: `tests/e2e/di/test_di_errors.py`

### DI-07: Circular dependency handling (risk: high)
- **Target**: `DependencyGraph.detect_cycles`, `ResolveCtx.in_cycle`
- **Test**: A→B→A cycle detected; self-loop detected; acyclic graph passes
- **File**: `tests/e2e/di/test_di_errors.py`

### DI-08: Override in tests (risk: medium)
- **Target**: `override_provider`, `spy_provider`, `DITestHarness.override`
- **Test**: Override → mock used → exit restores original
- **File**: `tests/e2e/di/test_di_overrides.py`

### DI-09: Concurrency stress (risk: high)
- **Target**: `resolve_async` under 500 concurrent calls
- **Test**: No data races, correct scope semantics
- **File**: `tests/e2e/di/test_di_concurrency.py`

### DI-10: Hot-rebind (risk: medium)
- **Target**: `TestContainer.register` overwrite, cache invalidation
- **Test**: Replace provider → new calls get new impl
- **File**: `tests/e2e/di/test_di_overrides.py`

### DI-11: Async provider init/teardown (risk: high)
- **Target**: Provider with `async_init()`, no hung tasks
- **Test**: Init completes, no leaked asyncio tasks after shutdown
- **File**: `tests/e2e/di/test_di_lifecycle.py`

### DI-12: Controller integration with DI (risk: high)
- **Target**: `ControllerFactory.create`, constructor injection
- **Test**: Controller gets correct DI instances; override propagates; singleton mode
- **File**: `tests/e2e/di/test_di_controller_integration.py`

### DI-13: DI + background worker context (risk: medium-high)
- **Target**: App container resolution outside HTTP request scope
- **Test**: Workers resolve singletons, share state with HTTP handlers
- **File**: `tests/e2e/di/test_di_controller_integration.py`

---

## Chaos & Fuzz Scenarios

| Scenario | File | Risk |
|----------|------|------|
| Factory intermittent failures under concurrency | `test_di_chaos.py` | high |
| Provider init crash → no half-open state | `test_di_chaos.py` | high |
| Harness failure injection + restore | `test_di_chaos.py` | medium |
| Fuzz token names (empty, 10K chars, unicode, injections) | `test_di_fuzz.py` | medium |
| Provider metadata edge cases | `test_di_fuzz.py` | low |
| Cache key collisions | `test_di_fuzz.py` | medium |

## Controller + DI Combined Scenarios

| Scenario | File | Risk |
|----------|------|------|
| Slow provider + 200 concurrent requests | `test_controller_di_stress.py` | high |
| Removed provider → fail fast + recovery | `test_controller_di_stress.py` | high |
| Corrupted cached instance detection | `test_controller_di_stress.py` | medium |

---

## Running

```bash
# DI tests only
python -m pytest tests/e2e/di/ -v --tb=short

# Full suite with JUnit output
python -m pytest tests/e2e/ -v --tb=short --junitxml=tests/e2e/report.xml
```
