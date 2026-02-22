# DI Regression Tests

## Overview

This directory contains comprehensive regression tests for the Aquilia DI system (`aquilia/di/`), covering provider resolution, scope semantics, lifecycle hooks, error handling, concurrency stress, controller integration, chaos, and fuzzing.

## Directory Structure

```
tests/e2e/di/
├── conftest.py                      # Shared fixtures and dummy services
├── harness/
│   ├── __init__.py
│   └── harness.py                   # DI test harness (introspection, overrides, failure injection)
├── test_di_resolution.py            # DI-01, DI-02, DI-03
├── test_di_lifecycle.py             # DI-04, DI-11
├── test_di_errors.py                # DI-05, DI-06, DI-07
├── test_di_overrides.py             # DI-08, DI-10
├── test_di_concurrency.py           # DI-09
├── test_di_controller_integration.py # DI-12, DI-13
├── test_di_chaos.py                 # Chaos scenarios
└── test_di_fuzz.py                  # Fuzz tests
```

## Running Tests

```bash
# All DI tests
python -m pytest tests/e2e/di/ -v --tb=short

# Specific test case
python -m pytest tests/e2e/di/test_di_resolution.py::TestDI01ProviderResolution -v

# With JUnit output
python -m pytest tests/e2e/di/ -v --junitxml=tests/e2e/report.xml

# Combined with controller stress tests
python -m pytest tests/e2e/di/ tests/e2e/controllers/test_controller_di_stress.py -v
```

## DI Test Harness

The `DITestHarness` provides runtime utilities for DI testing:

```python
from tests.e2e.di.harness import DITestHarness

harness = DITestHarness(container)

# Introspect
harness.list_providers()      # [{key, name, token, scope, tags}, ...]
harness.list_cached()         # {cache_key: instance}
harness.provider_count()      # int

# Instrument (count calls, measure time)
instr = harness.instrument("my_token")
await container.resolve_async("my_token")
print(instr.call_count, instr.total_time)

# Override (temporary mock)
async with harness.override("my_token", mock_value):
    result = await container.resolve_async("my_token")  # returns mock_value

# Failure injection
async with harness.inject_failure("my_token", RuntimeError("boom")):
    await container.resolve_async("my_token")  # raises RuntimeError
```

## Environment

- **Python**: 3.10+
- **Dependencies**: `pytest`, `pytest-asyncio` (auto mode)
- **Database**: None required (DI tests use in-memory providers)
- **No external services needed** — all tests are self-contained
