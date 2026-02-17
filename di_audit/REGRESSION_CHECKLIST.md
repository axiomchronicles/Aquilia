# Regression Checklist — DI + Models/DB Optimizations

## Quick Validation

```bash
# 1. Full test suite (must be 3527+ pass, 0 fail)
python -m pytest -x -q --tb=short

# 2. DI + models subset (must be 390 pass)
python -m pytest tests/test_di.py tests/test_models_orm.py tests/test_models_integration.py tests/test_db_integration.py -x -q

# 3. DI benchmark (check for regressions)
python benchmarks/bench_di.py

# 4. Models benchmark
python benchmarks/bench_models.py
```

---

## Detailed Regression Checks

### DI Subsystem (`aquilia/di/core.py`)

- [ ] `resolve_async` cached hit returns correct instance (type token)
- [ ] `resolve_async` cached hit returns correct instance (string token)
- [ ] `resolve_async` cold miss instantiates ClassProvider correctly
- [ ] `resolve_async` cold miss with dependencies resolves chain
- [ ] `resolve_async` with `optional=True` returns None for missing
- [ ] `resolve_async` with `tag` disambiguates correctly
- [ ] `create_request_scope()` inherits parent providers
- [ ] Singleton scope delegates to parent container
- [ ] `shutdown()` calls finalizers in LIFO order
- [ ] FactoryProvider cold resolution works
- [ ] ValueProvider cached resolution works
- [ ] `_type_key_cache` handles generic types (e.g., `List[int]`)
- [ ] `_CACHEABLE_SCOPES` includes singleton, app, request
- [ ] ResolveCtx cycle detection works (push/pop/in_cycle)

**Test files**: `tests/test_di.py`

### Models Metaclass (`aquilia/models/metaclass.py`)

- [ ] `_non_m2m_fields` excludes ManyToManyField instances
- [ ] `_non_m2m_fields` preserves field order
- [ ] `_non_m2m_fields` includes all non-M2M fields (AutoField, CharField, etc.)
- [ ] `_col_to_attr` maps column_name → (attr_name, field) correctly
- [ ] `_col_to_attr` handles custom `db_column` names
- [ ] Abstract models don't break metaclass processing

**Test files**: `tests/test_models_orm.py`

### Model Base (`aquilia/models/base.py`)

- [ ] `__init__` sets all non-M2M field defaults correctly
- [ ] `__init__` skips M2M fields without error
- [ ] `from_row` with column_name keys works (primary path)
- [ ] `from_row` with attr_name keys works (fallback path)
- [ ] `from_row` with mixed keys works
- [ ] `create()` persists all non-M2M fields
- [ ] `create()` handles auto-PK (AutoField/BigAutoField)
- [ ] `create()` applies pre_save hooks (auto_now_add)
- [ ] `create()` applies field defaults
- [ ] `bulk_create()` handles multiple instances
- [ ] `bulk_create()` with batch_size works
- [ ] `bulk_create()` with ignore_conflicts works
- [ ] `save()` insert path handles force_insert with explicit PK
- [ ] `save()` update path skips M2M fields
- [ ] `save()` with update_fields only updates specified fields
- [ ] `generate_create_table_sql()` includes all non-M2M columns
- [ ] `generate_create_table_sql()` excludes M2M fields

**Test files**: `tests/test_models_orm.py`, `tests/test_models_integration.py`

### Query Builder (`aquilia/models/query.py`)

- [ ] `_build_filter_clause` with lookup registry (exact, gt, contains, etc.)
- [ ] `_build_filter_clause` with F() expressions
- [ ] `_build_filter_clause` with `ne` operator (legacy path)
- [ ] `_build_filter_clause` with `ilike` operator (legacy path)
- [ ] `_cached_lookup_registry` lazily initialized on first call
- [ ] `_EXPR_OP_MAP` covers exact, gt, gte, lt, lte, ne
- [ ] Q chain immutability preserved (filter returns new Q)
- [ ] Q._clone() copies all fields correctly

**Test files**: `tests/test_models_orm.py`, `tests/test_models_integration.py`

### DB Engine (`aquilia/db/engine.py`)

- [ ] Connection with retry logic works
- [ ] Transaction context manager commits on success
- [ ] Transaction context manager rolls back on error
- [ ] Savepoint management works
- [ ] Multi-backend adapter selection (sqlite, postgresql, mysql)

**Test files**: `tests/test_db_integration.py`

---

## Performance Regression Thresholds

| Metric | Expected | Alert If |
|--------|----------|----------|
| resolve_async (cached, type) | ≤0.25µs | >0.50µs |
| resolve_async (cached, str) | ≤0.17µs | >0.35µs |
| resolve_async (cold, no deps) | ≤1.00µs | >2.00µs |
| Full lifecycle (1 resolve) | ≤0.60µs | >1.20µs |
| Model.__init__ (6 fields) | ≤1.20µs | >2.40µs |
| Model.from_row (8 cols) | ≤1.00µs | >2.00µs |
| Q().filter() (1 clause) | ≤1.30µs | >2.60µs |
| Full test suite | ≤8.00s | >12.00s |
